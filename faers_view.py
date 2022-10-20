import os
import re
import copy
import traceback as tb
import pandas as pd
from datetime import datetime as dt
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect

from ratelimit.decorators import ratelimit

from django.http import FileResponse, Http404
from django.conf import settings
from django.core.files.storage import FileSystemStorage

from utils.simple_file_rw import *
from utils.draw_graph import count_yearly
from utils.login_checker import check_login
from utils.faers_api import (
    do_advanced_search, make_result_per_session,
    search_with_faers_query,
)
import logging
logger = logging.getLogger('my')


@csrf_exempt
def download_faers_zip_result(request, zip_name):

    # logger.info(f"Download:\t{zip_name}")
    data_stored_in:str = os.path.abspath(os.path.join(
        settings.STATIC_ROOT, 'image'
    ))
    if not os.path.exists(data_stored_in):
        raise Http404

    zip_name = os.path.join(data_stored_in, zip_name)
    if not os.path.exists(zip_name):
        raise Http404

    fs = FileSystemStorage(zip_name)
    context = FileResponse(
        fs.open(zip_name, 'rb'), as_attachment=True
    )
    
    return context

@csrf_exempt
@ratelimit(key='ip', rate='200/m', method=ratelimit.ALL, block=True)
@ratelimit(key='ip', rate='100000/d', method=ratelimit.ALL, block=True)
def search_faers(request):

    logger.info(f'search_faers....{request.path}')

    if check_login(request, logger):
        return redirect(f'{settings.LOGIN_URL}?next={request.path}')

    search_result:dict = {}
    show_graph:bool = False
    uploaded_file_url:str = ''
    invalid_ftype:bool = False
    is_advanced_search:bool = False
    context = {
        'search_result': search_result,
        'json_name': 'faers_result',
        'uploaded_file_url': uploaded_file_url,
        'show_graph': show_graph,
        'invalid_ftype': invalid_ftype,
        'min_idx': 0,
        'max_idx': 10,
    }

    if request.method == 'POST':

        logger.info(f"post method: {request.POST}")
        logger.info(f"post method files: {request.FILES}")
        if 'uploadingFile' in request.FILES.keys() and \
            request.FILES['uploadingFile']:

            myfile = request.FILES['uploadingFile']
            # logger.info(f"{myfile.__dict__}")
            if myfile.content_type != 'text/tab-separated-values':
                context['invalid_ftype'] = True
                return render(request, 'main/faers.html', context)

            fs = FileSystemStorage()
            filename = fs.save(myfile.name, myfile)
            uploaded_file_url = fs.url(filename)
            local_file_path:str = os.path.join(
                settings.BASE_DIR, 'image', filename
            )

            try:
                # logger.info(local_file_path)
                search_word_list = pd.read_csv(local_file_path, sep='\t')
                # logger.info(search_word_list)
                ## TODO: Make result consecutively/asynchronously
                sesseion_done:bool = False
                for _, row in search_word_list.iterrows():
                    context['search_result'], context['show_graph'] = \
                        make_result_per_session(
                            row.to_dict(), settings.STATIC_ROOT, logger
                        )
                    sesseion_done = True
                    break
                
            except:
                logger.error("Can't load the uploaded file")
                logger.error(tb.format_exc())
                context['invalid_ftype'] = True
                context['uploaded_file_url'] = filename

            # logger.info(context)

            return render(request, 'main/faers.html', context)

        else:
            
            data = request.POST
            if ('search_word' in data.keys() and data['search_word']!=''):

                logger.info(f"Search for the following one: {data}")

                if data['count_by']=='year':

                    context['search_result'], context['show_graph'] = \
                        make_result_per_session(
                            data, settings.STATIC_ROOT, logger
                        )

                else:

                    if data['regroup_by'] == 'none':
                        context['search_result'], context['show_graph'] = \
                            make_result_per_session(
                                data, settings.STATIC_ROOT, logger
                            )
                    else:
                        process_done = False
                        adv_callback = \
                            do_advanced_search(
                                data, settings.STATIC_ROOT, logger
                            )
                        context['search_result'] = adv_callback[0]
                        context['show_graph'] = adv_callback[1]
                        downloadable_zip = adv_callback[2]

                        context['is_advanced_search'] = True
                        context['downloadable_zip'] = \
                            os.path.basename(downloadable_zip)
    # logger.info(context)

    return render(request, 'main/faers.html', context)

@csrf_exempt
@ratelimit(key='ip', rate='200/m', method=ratelimit.ALL, block=True)
@ratelimit(key='ip', rate='100000/d', method=ratelimit.ALL, block=True)
def determine_faers_query(request):

    logger.info(f'search_faers....{request.path}')

    if check_login(request, logger):
        return redirect(f'{settings.LOGIN_URL}?next={request.path}')

    context:dict = {
        'search_result': None, 'has_result': False,
        'query': "", "has_yearly_image": False,
        'json_name': "query_result",
    }
    rendering_templetes = ['main/faers_query.html', 'main/base_faers.html']
    if request.method == 'POST':

        data = request.POST
        if ('search_query' not in data.keys() or data['search_query']==''):
            raise Http404('Please Enter a Query')
        
        context['search_result'] = search_with_faers_query(data, logger)
        context['query'] = data['search_query']
        context['has_result'] = True

        if data['search_query'].find('count=')!=-1:
            
            if 'results' in context['search_result'].keys():

                df = pd.DataFrame(context['search_result']['results'])
                logger.info(f"Query Result: {df.shape}")
                if data['search_query'].find('count=receivedate')!=-1:
                    df_year = copy.deepcopy(df)
                    df_year['year'] = [year[:4] for year in df_year['time']]
                    df_year = df_year.groupby('year', as_index=False).sum()
                    count_yearly(
                        save_in=settings.STATIC_ROOT, yearly_df=df_year
                    )
                    context['has_yearly_image'] = True

                    description = '\n'.join(
                        df.describe().to_html().split('\n')[1:]
                    )
                    description = re.sub(
                        '\sstyle=["\s\w\d\-]{1,}[:]?[\s]?[\w\d\-\%]{1,};"',
                        '',
                        description
                    )
                    html_path:str = os.path.join(
                        settings.BASE_DIR, 'main/templates/main/dataframe.html' 
                    )
                    with open(html_path, 'w') as wh:

                        wh.write('{% load static %}\n\n')
                        if context['has_yearly_image']:
                            wh.write('<div id="chart_loc">\n')
                            wh.write('\t<img src="{% static \'image/query_yearly_chart.png\' %}" alt="No image" id="query_test_yearly_chart">\n')
                            wh.write('</div>\n')

                        wh.write('<div class="table-reponsive">\n')
                        wh.write(
                            '<table class="table table-striped table-bordered table-hover">\n'
                        )
                        wh.write(
                            f'\t<caption>Yearly Chart Description {dt.now()}</caption>\n'
                        )
                        wh.write(description)
                        wh.write('\n</div>')

    logger.info(f"faers query test:\t{context}")

    return render(request, rendering_templetes, context)
