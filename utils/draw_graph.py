import re
import numpy as np
import PIL as pil
import pandas as pd
import matplotlib.pyplot as plt
from os import walk
from os.path import abspath, basename, dirname, exists, join as jn


def set_save_name(fname:str, regroup_by:str='', extension:str='.png') -> str:
    
    ii:int = 1
    while exists(fname):
        fname = jn(
            dirname(fname),
            basename(fname).replace(
                f'{extension}', f'_{regroup_by}{ii:04}{extension}'
            ) if basename(fname).find(regroup_by)==-1 \
                else basename(fname)[:-8]+f'{ii:04}{extension}'
        )
        ii += 1
        # if ii > 21:
        #     break
    return fname

def regularize_reaction_name(df:pd.DataFrame) -> pd.DataFrame:
    
    ## Grouping similar names
    df['term'] = df['term'].str.title()
    df['term'] = df['term'].str.replace('^S', "'s", regex=False)
    if df.shape[0] != len(df.term.unique()):
        df = df.groupby('term', as_index=False).sum()
    
    return df

def regularize_drug_name(df:pd.DataFrame) -> pd.DataFrame:
    
    ## Grouping similar names
    df['term'] = df['term'].str.lower()
    df['term'] = df['term'].str.replace('^s', "'s", regex=False)
    df['term'] = df['term'].str.replace('tablet', "", regex=False)
    df['term'] = df['term'].str.replace('oral', "", regex=False)
    df['term'] = df['term'].str.replace('extra strength', "", regex=False)
    df['term'] = df['term'].str.replace('capsule[s\s]*', "", regex=True)
    df['term'] = df['term'].str.replace('film[-\s]*coat[ed\s]*', "", regex=True)
    df['term'] = df['term'].str.replace(
        '[,\s]*extend[ed\s]*release', "", regex=True
    )
    df['term'] = df['term'].str.replace(
        '[\s,]*[\d\.]+[\s]?[\w]g', "", regex=True
    )
    df['term'] = df['term'].str.strip()
    if df.shape[0] != len(df.term.unique()):
        df = df.groupby('term', as_index=False).sum()
    
    return df

def count_by_element(
    data:dict,
    save_in:str,
    search_word:str,
    count_by:str,
    logger,
    is_advanced_search:bool=False,
) -> pd.DataFrame:
    
    df = pd.DataFrame(data['results'])

    ## Grouping similar names
    if count_by =='drug':
        df = regularize_drug_name(df)
    elif count_by =='reaction':
        df = regularize_reaction_name(df)

    df.sort_values(
        by='count', ascending=[True],
        inplace=True, ignore_index=True
    )

    fig_config:dict = dict(
        figsize=(14,7), dpi=300,
    )
    tick_params1:dict = dict(
        which='both', bottom=False,
        top=False, labelbottom=False
    )
    tick_params2:dict = dict(
        rotation=45
    )
    tick_params3:dict = dict(
        which='both', left=False,
        right=False, labelleft=False
    )
    graph_for = count_by.title()

    fig, ax = plt.subplots(
        nrows=1, ncols=2,
        sharex=False, sharey=False,
        **fig_config
    )
    # fig.tight_layout()

    names = df.iloc[:,0]
    counts = df.iloc[:,1]
    info = f"# of {graph_for}s: {len(names)}"
    ax[0].plot(names, counts)
    ax[0].set_xlabel(f'{graph_for}s')
    ax[0].set_ylabel('# of Reports')
    ax[0].text(0.1, counts.max(), info, ha='left', va='center')
    ax[0].set_title(
        f'All {graph_for}s Relate to\n{search_word.title()}'
    )
    ax[0].tick_params(axis='x', **tick_params1)
    ax[0].grid(axis='y', which='major', color='0.95')

    limit:int = 20
    names = df.iloc[-20:,0]
    counts = df.iloc[-20:,1]
    mx_cnt = counts.max()
    if df.shape[0]<20:
        limit = df.shape[0]
    mx_cnt = counts.max()
    ax[1].barh(names, counts, color='#D3D3D3')
    ax[1].set_title(f'Top {limit} {graph_for}s')
    ax[1].set_xlabel('# of Reports')
    ax[1].set_ylabel(f'{graph_for}s')
    ax[1].tick_params(axis='x', **tick_params2)
    ax[1].tick_params(axis='y', **tick_params3)
    ax[1].grid(axis='x', which='major', color='0.95')

    x_pos:int = mx_cnt//20 if mx_cnt > 100 \
        else mx_cnt//10 if 10<mx_cnt<=100 \
        else mx_cnt//2
    for ii, (n, v) in enumerate(zip(names, counts)):
        ax[1].text(
            x=x_pos, y=ii, s=f"{n}:  {v:,}",
            color='black', fontsize=9,
            ha='left', va='center'
        )

    fig_fname:str = f"{save_in}/image/chart.png"
    if is_advanced_search:
        fig_fname = set_save_name(fig_fname, count_by)
    fig.savefig(fig_fname)

    plt.cla()
    plt.clf()
    plt.close()

    df.sort_values(
        by='count', ascending=[False],
        inplace=True, ignore_index=True
    )

    return df

def count_yearly(
    data:dict=None, save_in:str=None,
    search_info:str=None, logger=None, yearly_df=None
) -> None:
    
    if yearly_df is None:
        search_type:str = search_info['search_type']
        search_word:str = search_info['search_word'].title() \
            if search_type=='reactionmeddrapt' \
            else search_info['search_word'].lower()
        df = pd.DataFrame(data['results'])

        ## Grouping yearly
        df['year'] = [t[:4] for t in df['time']]
        yearly = df.groupby('year', as_index=False).sum()
        # logger.info(yearly)
        img_save_name = f"{save_in}/image/chart.png"
    else:
        yearly = yearly_df
        search_word:str = 'query'
        img_save_name = f"{save_in}/image/query_yearly_chart.png"

    fig_config:dict = dict(
        figsize=(6,7), dpi=300,
    )
    tick_params1:dict = dict(
        rotation=45
    )
    tick_params2:dict = dict(
        which='both', left=False,
        right=False, labelleft=False
    )

    fig, ax = plt.subplots(
        nrows=1, ncols=1,
        sharex=False, sharey=False,
        **fig_config
    )
    years = yearly.iloc[:,0]
    counts = yearly.iloc[:,1]
    mx_cnt = counts.max()
    info:str = f"Total Reports: {counts.sum():,}"
    ax.barh(years, counts, color='#D3D3D3')
    ax.set_ylabel('Year')
    ax.set_xlabel('# of Reports')
    ax.set_title(f'Yearly Report for\n{search_word}')
    ax.text(
        x=counts.max()*0.7, y=yearly.shape[0]*0.95, s=info,
        ha='left', va='center'
    )
    ax.tick_params(axis='x', **tick_params1)
    ax.tick_params(axis='y', **tick_params2)
    ax.grid(axis='x', which='major', color='0.95')

    x_pos:int = mx_cnt//20 if mx_cnt > 100 \
        else mx_cnt//10 if 10<mx_cnt<=100 \
        else mx_cnt//2
    for ii, (n, v) in enumerate(zip(years, counts)):
        ax.text(
            x=x_pos, y=ii, s=f"{n}:  {v:,}",
            color='black', fontsize=9,
            ha='left', va='center'
        )
    fig.savefig(img_save_name)

    plt.cla()
    plt.clf()
    plt.close()

    return

def find_images(target_folder:str) -> list:
    
    images_to_merge:list = sorted([
        abspath(jn(root, file))
        for root, _, files in walk(f"{target_folder}/image")
        for file in files
        if re.match('^chart_(drug|reaction)[\d]{4}\.png$', file)
    ])

    return images_to_merge

def merge_images(save_in:str, logger) -> list:
    
    images_to_merge:list = find_images(save_in)
    # logger.info(images_to_merge)
    pil.ImageFile.LOAD_TRUNCATED_IMAGES = True
    imgs = [
        pil.Image.open(fname)
        for fname in images_to_merge
    ]
    min_shape = sorted([
        (np.sum(img.size), img.size)
        for img in imgs
    ])[0][1]
    img_merged = np.vstack((
        np.asarray(img.resize(min_shape))
        for img in imgs
    ))
    img_merged = pil.Image.fromarray(img_merged)
    merged_img_fname:str = abspath(f"{save_in}/image/chart_merged.png")
    img_merged.save(merged_img_fname)
    images_to_merge.append(merged_img_fname)

    return images_to_merge
