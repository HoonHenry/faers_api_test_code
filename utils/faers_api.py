import pytz
import subprocess as sp
import pandas as pd
import requests as rq
from datetime import datetime as dt
from os.path import abspath, basename

from utils.draw_graph import (
    count_by_element, count_yearly, merge_images,
    regularize_drug_name, regularize_reaction_name, set_save_name
)

"""
    _summary_
    With an API key:
        240 requests per minute, per key.
        120,000 requests per day, per key.

    _worked query_
    https://api.fda.gov/drug/event.json?search=receivedate=[20040101+TO+20220901]
    total: 15234431

    https://api.fda.gov/drug/event.json?search=receivedate:[20040101+TO+20220901]
    total: 15234055
    
    https://api.fda.gov/drug/event.json?search=patient.drug.generic_name=rosiglitazone
    total: 50972

    https://api.fda.gov/drug/event.json?search=patient.drug.activesubstance.activesubstancename=rosiglitazone
    total: 50972

    https://api.fda.gov/drug/event.json?search=patient.reaction.reactionmeddrapt=headache
    total: 734637

    https://api.fda.gov/drug/event.json?search=patient.reaction.reactionmeddrapt:headache
    total: 482129
    
    https://api.fda.gov/drug/event.json?search=(receivedate:[20040101+TO+20220915])+AND+generic_name=liraglutide+AND+drugchracterization=1&count=patient.reaction.reactionmeddrapt.exact

    https://api.fda.gov/drug/event.json?search=(receivedate:[20040101+TO+20220915])+AND+reactionmeddrapt=alopecia&count=patient.drug.openfda.generic_name.exact

    https://api.fda.gov/drug/event.json?search=(receivedate:[19680101+TO+20081231])+AND+patient.drug.activesubstance.activesubstancename.exact=minoxidil&count=patient.reaction.reactionmeddrapt.exact

    https://api.fda.gov/drug/event.json?search=(receivedate:[20040101+TO+20220926])+AND+rosiglitazone&count=patient.drug.openfda.generic_name.exact

    https://api.fda.gov/drug/event.json?search=(receivedate:[20040101+TO+20220926])+AND+(activesubstance=rosiglitazone)+AND+(reactionmeddrapt=myocardial+infarction)&count=patient.drug.openfda.generic_name.exact
"""

def search_from_faers_api(
    info:dict, logger,
) -> list:
    
    base_url:str = "https://api.fda.gov/drug/event.json"
    api_key:str = "api_key=MiCTGO2F1rEgZgjNQMpVYYYTSSAehGBLy6W7ToTK"
    current_date:str = dt.now().strftime("%Y%m%d")
    valid_search_type:list = [
        'reactionmeddrapt', 'reaction', 'disease',
        'activesubstance', 'drug'
    ]

    if info['search_type'] not in valid_search_type:
        logger.error(
            f'Invalid search type while searching: {info["search_type"]}'
        )
        raise TypeError(
            f'Invalid search type while searching: {info["search_type"]}'
        )

    # search_type = info['search_type']
    
    if info['search_type']=='disease':
        search_type = 'patient.drug.drugindication'
    else:
        search_type = 'patient.drug.activesubstance.activesubstancename'
    count_option = info['count_by']
    word = info['search_word']
    regroup_by:str = ''
    adv_search_word:str = ''

    date_limit:str = f"(receivedate:[19680101+TO+{current_date}])+AND+" \
        if count_option in valid_search_type \
        else ''
    
    if count_option=='year':
        pass

    elif all(
        ky in info.keys() and (info[ky]!='' and info[ky] is not None)
        for ky in ['regroup_by', 'adv_search_word']
    ):
    # if info['adv_search_word']!='' and info['adv_search_word'] is not None:
        if info['regroup_by'] not in ['reaction', 'drug']:
            logger.error(f'Invalid advance search type: {info["regroup_by"]}')
            raise TypeError(
                f'Invalid advance search type: {info["regroup_by"]}'
            )
        regroup_by = 'reactionmeddrapt' if info['regroup_by']=='reaction' \
            else 'activesubstance'
        adv_search_word = info['adv_search_word'].replace(' ', '+').lower()
        if regroup_by not in valid_search_type:
            logger.error(f'Invalid regroup type while searching: {regroup_by}')
            raise TypeError(
                f'Invalid regroup type while searching: {regroup_by}'
            )
        adv_search_word = f"+AND+({regroup_by}={adv_search_word})"

    else:
        
        if info['regroup_by']!='none':
            count_option = info['regroup_by']
        # logger.info(f"{info['regroup_by']}, {info['adv_search_word']}, {type(info)}")
        # raise ValueError('Incorrect')

    logger.info(f"{search_type}, {count_option}, {word}")
    count_type:str = '&count=receivedate' \
        if count_option=='year' \
        else '&count=patient.drug.openfda.generic_name.exact' \
            if count_option=='drug' \
        else '&count=patient.reaction.reactionmeddrapt.exact' \
            if count_option=='reaction' \
        else ''

    is_multiple_words:bool = False
    if word.find('drug:')!=-1 or word.find('disease:')!=-1:
        # word = search_word_type_checker(word, search_type)
        pass
    else:
        if word.find(' and ')!=-1 or word.find(' AND ')!=-1:
            word = word.replace(' and ', '+AND+')
            is_multiple_words = True
        if word.find(' or ')!=-1 or word.find(' OR ')!=-1:
            word = word.replace(' or ', '+OR+')
            is_multiple_words = True
        if is_multiple_words:
            word = f"({word})"
    
    word = word.replace(' ', '+')
    # word_to_search:str = \
    #     f"{date_limit}({search_type}={word}){adv_search_word}" \
    #     if is_multiple_words \
    #     else f"{date_limit}({search_type}={word}){adv_search_word}"
    word_to_search:str = \
        f"{date_limit}({search_type}:{word}){adv_search_word}"

    url:str = f"{base_url}?{api_key}&search={word_to_search}{count_type}"
    logger.info(f"search query: {url}")
    req = rq.get(url=url)
    code = req.status_code
    callback_from_faers_api = req.json()
    # logger.info(req)

    if code==200:
        # logger.info(callback_from_faers_api)
        logger.info('openFDA call succeeded')
    else:
        logger.error(f'Something invalid; {code}')
        logger.error(f'Something invalid; {info["search_type"]}')

    return callback_from_faers_api

def make_result_per_session(data, static_path, logger) -> tuple or dict:
    
    search_list = search_from_faers_api(
        info=data,
        logger=logger
    )
    show_graph:bool = False
    # logger.info(search_list.keys())
    valid_search_type:list = [
        'reactionmeddrapt', 'reaction', 'disease',
        'activesubstance', 'drug'
    ]

    if 'error' not in search_list.keys():

        if data['search_type'] not in valid_search_type:
            raise TypeError(
                f'Invalid search type: {data["search_type"]}'
            )

        if data['count_by']=='year':

            count_yearly(
                search_list,
                static_path,
                data,
                logger
            )

        elif data['count_by'] in ['drug', 'reaction']:

            count_by_element(
                data=search_list,
                save_in=static_path,
                search_word=data['search_word'],
                count_by=data['count_by'],
                logger=logger,
            )

        show_graph = True

    return search_list, show_graph

def do_advanced_search(data, static_path, logger) -> tuple or dict:
    
    show_graph:bool = False
    search_type:str = data['search_type']
    regroup_by:str = data['regroup_by']
    min_idx:int = int(data['min_idx'])
    max_idx:int = int(data['max_idx'])
    adv_search_info:dict = {
        'search_word': data['search_word'],
        'search_type': search_type,
        'count_by': data['count_by'],
        'regroup_by': regroup_by,
        'adv_search_word': None,
    }

    ## search for the given word
    search_list = search_from_faers_api(
        info=adv_search_info,
        logger=logger
    )
    valid_search_type:list = [
        'reactionmeddrapt', 'reaction', 'disease',
        'activesubstance', 'drug'
    ]

    if search_type not in valid_search_type:
        raise TypeError(
            f'Invalid search type: {search_type}'
        )

    if 'error' not in search_list.keys():
    
        ## pick the word to do advanced search
        df = pd.DataFrame(search_list['results'])
        if regroup_by=='drug':
            df = regularize_drug_name(df)
        elif regroup_by=='reaction':
            df = regularize_reaction_name(df)
        else:
            raise TypeError(f'Invalid regroup type: {regroup_by}')
        df = df.iloc[min_idx:max_idx,:]
        logger.info(f'Regroup size:\t{df.shape}')
        
        adv_search_result:list = [] 
        result_merged:pd.DataFrame = pd.DataFrame()
        for ii, row in df.iterrows():

            adv_search_info['adv_search_word'] = row['term']
            logger.info(f"{ii+1} th {adv_search_info}")

            search_list2 = search_from_faers_api(
                info=adv_search_info,
                logger=logger
            )
            fig_title_name:str = f"{data['search_word']} and {row['term']}"

            single_search_result:pd.DataFrame = count_by_element(
                data=search_list2,
                save_in=static_path,
                search_word=fig_title_name,
                count_by=adv_search_info['count_by'],
                logger=logger,
                is_advanced_search=True
            )

            ## Merging data from openFDA
            single_result_size:int = single_search_result.shape
            single_search_result.insert(
                0, 'search_for', [fig_title_name]*single_result_size[0]
            )
            result_merged = pd.concat(
                objs=[result_merged, single_search_result],
                axis=0,
            )

            adv_search_result.append({
                'search_for': fig_title_name,
                'result': search_list2,
            })
            
        data_fname:str = abspath(f"{static_path}/image/data.tsv")
        result_merged.to_csv(data_fname, sep='\t', index=False,)

        files_to_deflate:list = merge_images(static_path, logger)
        files_to_deflate = [
            basename(fname) for fname in files_to_deflate
        ]
        files_to_deflate.append(basename(data_fname))
        files_to_deflate_cmd1:str = ' '.join(files_to_deflate)
        chart_fname:str = "chart_merged.png"
        files_to_deflate.remove(chart_fname)
        files_to_deflate_cmd2:str = ' '.join(files_to_deflate)

        data_stored_in:str = abspath(f"{static_path}/image")
        cur_time:str = dt.now(pytz.timezone('Asia/Seoul'))
        timestamp = cur_time.strftime("%y%m%d%H%M%S")
        zip_name:str = set_save_name(
            fname=f"{data_stored_in}/data_{timestamp}.zip",
            extension='.zip'
        )
        cmd:str = f"cd {data_stored_in}; " + \
            f"zip {zip_name} {files_to_deflate_cmd1}; " + \
            f"rm -v {files_to_deflate_cmd2}"
        # logger.info(cmd)
        p = sp.Popen(cmd, shell=True, stdout=sp.PIPE)
        out, err = p.communicate()
        if out:
            logger.info(out.decode('utf-8'))
        if err:
            logger.error(out.decode('utf-8'))

        show_graph = True

    return adv_search_result, show_graph, zip_name

def search_with_faers_query(
    info:dict, logger,
) -> dict:
    
    base_url:str = "https://api.fda.gov/drug/event.json"
    api_key:str = "api_key=MiCTGO2F1rEgZgjNQMpVYYYTSSAehGBLy6W7ToTK"
    current_date:str = dt.now().strftime("%Y%m%d")
    query = info['search_query']

    url:str = f"{base_url}?{api_key}&search=(receivedate:[19680101+TO+{current_date}])+AND+{query}"
    logger.info(f"search query: {url}")
    req = rq.get(url=url)
    # logger.info(f"result json: {req.json()}")

    if req.status_code != 200:
        logger.error(req)

    result = req.json()

    return result
