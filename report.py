#!/usr/bin/python3
import logging
import os
import re
import datetime
import pandas as pd
from takeout import TakeoutHTMLReader
from urllib.request import build_opener
from urllib.error import HTTPError
from urllib.parse import urlencode
import json
import googleapiclient.discovery
import math
from dateutil import parser
import isodate
# __version__ = "0.5.5"
# __author__ = "np1"
# __license__ = "LGPLv3"

# YouTube 分类id转名字
PFX = "https://www.googleapis.com/youtube/v3/"
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
INDICT = {
    1: 'Film & Animation',
    2: 'Autos & Vehicles',
    10: 'Music',
    15: 'Pets & Animals',
    17: 'Sports',
    18: 'Short Movies',
    19: 'Travel & Events',
    20: 'Gaming',
    21: 'Videoblogging',
    22: 'People & Blogs',
    23: 'Comedy',
    24: 'Entertainment',
    25: 'News & Politics',
    26: 'Howto & Style',
    27: 'Education',
    28: 'Science & Technology',
    29: 'Nonprofits & Activism',
    30: 'Movies',
    31: 'Anime / Animation',
    32: 'Action / Adventure',
    33: 'Classics',
    34: 'Comedy',
    35: 'Documentary',
    36: 'Drama',
    37: 'Family',
    38: 'Foreign',
    39: 'Horror',
    40: 'Sci - Fi / Fantasy',
    41: 'Thriller',
    42: 'Shorts',
    43: 'Shows',
    44: 'Trailers'
}

logger = logging.getLogger("uvicorn.default")


class TakeoutReport(TakeoutHTMLReader):
    api_keys = []

    def __init__(self, api_keys: list[str], path: str):
        self.api_keys = api_keys
        TakeoutHTMLReader.__init__(self, path)

    # YouTube api请求函数
    def generate_report(self):

        logger.info("generating report")
        # 实例化parse中的各个函数
        urls_id = self.find_video_id()
        channel_link = self.find_channel_link()
        channel_title = self.find_channel_title()
        video_title = self.find_video_title()
        date_time = self.find_date_time()

        # PD-dataframe
        df_urls_id = pd.DataFrame(urls_id)
        df_video_title = pd.DataFrame(video_title)
        df_channel_link = pd.DataFrame(channel_link)
        df_channel_title = pd.DataFrame(channel_title)
        df_time = pd.DataFrame(date_time)

        url_list = df_urls_id.iloc[:, 0].tolist()
        links_list = []
        for i in url_list:
            i = 'https://www.youtube.com/watch?v='+i
            links_list.append(i)
        df_urls_id['video_link'] = links_list
        df_urls_id = df_urls_id.rename(columns={0: "video_id"})

        df_time.columns = ['watch_time']
        time_list = []
        for i in df_time['watch_time']:
            i = time_format(i)
            time_list.append(i)
        df_time['watch_time'] = time_list

        time_day_list = []
        for i in df_time['watch_time']:
            match = re.match(r"\d{4}\-\d{2}\-\d{2}", i)
            if match is not None:
                i = match.group()
                time_day_list.append(i)
        df_time['watch_time_day'] = time_day_list

        df_new = pd.DataFrame(df_time.groupby(
            "watch_time_day").size()).reset_index()
        df_new.columns = ['watch_time', 'values']
        active_day = df_new['watch_time'].count()

        # 实例化search
        df_searches = self.search_history()
        for i, j in df_searches['DATE_TIME'].items():
            # 时间格式化
            k = time_format(j)
            df_searches.loc[i, 'DATE_TIME'] = k
        # 过滤非2022年数据
        if df_searches.shape[0] != 0:
            df_searches_yr = df_searches[df_searches['DATE_TIME'].str.contains(
                '2022')]
        else:
            df_searches_yr = df_searches

        # 实例化comment
        try:
            df_comments = self.comment_history()
        except TypeError:
            all_links = ""
        # 过滤非2022年数据
        if df_comments.shape[0] != 0:
            df_comments_yr = df_comments[df_comments['DATE_TIME'].str.contains(
                '2022')]
        else:
            df_comments_yr = df_comments

        # 实例化like
        try:
            df_likes = self.like_history()
        except FileNotFoundError:
            logger.info("No like history found")
            df_likes = pd.DataFrame(
                columns=["liked_video_id", 'liked_video_url', "liked_time"])
        # 过滤非2022年数据
        if df_likes.shape[0] >0:
            df_likes_yr = df_likes[df_likes['liked_time'].str.contains('2022')]
        else:
            df_likes_yr = df_likes

        df_yr = pd.concat([df_video_title, df_urls_id,
                          df_channel_link, df_channel_title, df_time], axis=1)
        df_yr.columns = ['video_title', 'video_id', 'video_link',
                         'channel_link', 'channel_title', 'watch_time', 'time_day']
        # filter 2022
        df_yr = df_yr[df_yr['watch_time'].str.contains('2022')]
        df_yr.drop(['time_day'], axis=1, inplace=True)
        # Convert to datetime
        for i, j in df_yr['watch_time'].items():
            df_yr.loc[i, 'watch_time'] = parser.parse(j).strftime('%Y-%m-%d')
        # 观看数
        watched_video = len(df_yr['video_id'])
        # 搜索数
        searches_yr = df_searches_yr['SEARCHES'].count()
        # 点赞数
        likes_yr = df_likes_yr['liked_video_id'].count()
        # 评论数
        comments_yr = df_comments_yr['COMMENTS'].count()
        # 活跃天数
        active_day = active_day
        # 全年活跃占比
        UpTime = '{:.2%}'.format(active_day/365)
        video_per_day = '{:.2f}'.format(watched_video/365)
        # csv相关
        stat_list_yr = [watched_video, searches_yr, likes_yr,
                        comments_yr, active_day, UpTime, video_per_day]
        dfstat_yr = pd.DataFrame(stat_list_yr).T
        dfstat_yr.columns = ['watched', 'searches', 'likes', 'comments',
                             'active_total_day', 'uptime', 'video_watched_per_day']
        # csv相关

        # TOP5_WATCH
        url_sizes = df_yr.groupby("video_id").size()
        sorted_watch = dict(url_sizes.sort_values(
            ascending=False))

        df_sorted_watch = pd.DataFrame(sorted_watch, index=[0]).T
        df_sorted_watch.reset_index(inplace=True)
        df_sorted_watch.columns = ['video_id', 'watch_time']
        df_top5 = pd.DataFrame({'watch_time_rank': [0], 'video_id': [
            0], 'video_link': [0], 'watch_times': [0], 'video_title': [0]})

        for i in range(5):

            find_title = df_yr[df_yr['video_id'] ==
                               df_sorted_watch.iloc[i, 0]].iloc[0, 0]

            list_top5 = ['TOP'+str(i+1), df_sorted_watch.iloc[i, 0],
                         'https://www.youtube.com/watch?v=' +
                         str(df_sorted_watch.iloc[i, 0]),
                         df_sorted_watch.iloc[i, 1],
                         find_title
                         ]
            df_top5.loc[i, :] = list_top5

        top5_json = df_top5.to_json(orient='records')
        df_time.columns = ['watch_time', 'watch_time_day']
        # csv相关

        # YouTube v3 api请求
        df_yr_dlc = pd.DataFrame({'publishedAt': 0, 'title': 0, 'categoryId': 0,
                                 'defaultAudioLanguage': 0, 'duration': 0, 'licensedContent': 0, }, index=[0])

        ids = df_yr['video_id']

        api_service_name = "youtube"
        api_version = "v3"

        api_keys = self.api_keys
        id_count = 0
        key_used = 0

        # 50个id一组
        def processing(id_count: int, i: int):
            youtube = googleapiclient.discovery.build(
                api_service_name, api_version, developerKey=self.api_keys[key_used])
            id_list = ids.to_list()[i:i+50]
            id_string = ','.join(id_list)
            request = youtube.videos().list(part='snippet,contentDetails', id=id_string)
            response = request.execute()
            # print(response)
            # 要用的只有categoryId/defaultAudioLanguage/duration
            for item in response.get('items', []):
                s1 = item.get('snippet', {})
                s1_names = ['publishedAt', 'title', 'categoryId',
                            'defaultAudioLanguage']  # 'tags','description'
                s1_ = {key: value for key,
                       value in s1.items() if key in s1_names}
                for k in s1_names:
                    if s1.get(k) != None:
                        continue
                    else:
                        s1_[k] = 'N/A'
                # 获取duration
                s2 = item.get('contentDetails', {})
                s2_names = ['duration', 'licensedContent']
                s2_ = {key: value for key,
                       value in s2.items() if key in s2_names}
                sz = {}
                sz.update(s1_)
                sz.update(s2_)
                dataz = list(sz.values())
                df_yr_dlc.loc[id_count, :] = dataz
                id_count += 1

        for i in range(0, len(ids), 50):
            # print(i)
            try:
                processing(id_count, i)
                id_count += 50
            except:
                key_used += 1
                logger.info(
                    f'Current API key is exceeded the quota, using next API key. Key count: {key_used}')
                if key_used+1 == len(api_keys):
                    raise Exception('API keys used up')
                processing(id_count, i)
                continue

        # 将duration数据转为seconds
        for i, j in df_yr_dlc['duration'].items():
            if j == 'N/A':
                continue
            else:
                total_seconds = int(
                    isodate.parse_duration(j).total_seconds())
                # Limit duration to 20 minutes if the video is longer than 20 minutes
                df_yr_dlc.loc[i, 'duration'] = total_seconds if total_seconds < 20*60 else 20*60

        df_yr_dlc = df_yr_dlc.reindex(columns=['title', 'publishedAt', 'categoryId', 'duration', 'licensedContent',
                                               'viewCount', 'likeCount', 'commentCount', 'defaultAudioLanguage'])

        # 下面都是导出csv
        dfstat_json = dfstat_yr.to_json()
        # 上面都是导出csv

        # 下面所有处理都是以df_yr_dlc为基础
        # duration (<1min, 1-5min, 5-10min, >10min)
        df_duration = df_yr_dlc.reindex(columns=['duration'])
        # print(df_duration)
        # I know it's a bit ugly
        below_one_minute = len(df_duration[df_duration['duration'] < 60])
        one_to_five = len(df_duration[(df_duration['duration'] >= 60) & (
            df_duration['duration'] < 300)])
        five_to_ten = len(df_duration[(df_duration['duration'] >= 300) & (
            df_duration['duration'] < 600)])
        above_ten = len(df_duration[df_duration['duration'] >= 600])
        df_duration_json = {
            'below_one_minute': below_one_minute,
            'one_to_five': one_to_five,
            'five_to_ten': five_to_ten,
            'above_ten': above_ten
        }
        # language
        df_lang = pd.DataFrame(dict(
            df_yr_dlc['defaultAudioLanguage'].value_counts(ascending=False)), index=[0]).T
        df_lang.reset_index(inplace=True)
        df_lang.columns = ['language', 'lanCounts']
        df_lang.drop(df_lang[df_lang['language'] == 'N/A'].index, inplace=True)
        # csv相关
        other = 0
        if len(df_lang) < 3:
            df_lang = df_lang.sort_index().reset_index(drop=True)
            df_lang['lanCounts'] = df_lang['lanCounts'].apply(int)
        else:
            for i, j in df_lang['lanCounts'].items():
                if i < 3:
                    continue
                else:
                    other += j
            df_lang.loc[3.5, :] = ['other', other]
            df_lang = df_lang.sort_index().reset_index(drop=True)
            df_lang['lanCounts'] = df_lang['lanCounts'].apply(int)
        # csv相关

        # categoryName & ~watchTime/~watchTime_min
        df_api_dlc = df_yr_dlc.copy(deep=False)
        df_api_dlc.insert(3, 'categoryName', value='NaN')
        for i, j in df_api_dlc['categoryId'].items():
            k = id_name(int(j))
            df_api_dlc.loc[i, 'categoryName'] = k

        # categoryWatchTimes
        # insert a new columns 'duration in seconds'
        df_api_dlc.insert(5, 'durations', value='NaN')

        for i, j in df_api_dlc['duration'].items():
            df_api_dlc.loc[i, 'durations'] = j

        # Generate category watch times
        df_calc_times = pd.DataFrame(df_api_dlc["categoryName"].value_counts())
        df_calc_times.reset_index(inplace=True)
        df_calc_times.columns = ['categoryName', 'watchTimes1']
        df_calc_times.dropna()

        # 类别观看时长（in minutes）
        dict_catDu = {}
        for i in INDICT.keys():
            if i == 0:
                continue
            dfid = df_api_dlc[df_api_dlc['categoryId'] == str(i)]
            dict_catDu[id_name(i)] = dfid['durations'].sum()
        df_total_duration = pd.DataFrame(dict_catDu, index=[0]).T
        df_total_duration.reset_index(inplace=True)
        df_total_duration.columns = ['categoryName', 'watchTime_min']
        for i, j in df_total_duration['watchTime_min'].items():
            df_total_duration.iloc[i, 1] = '{:.2f}'.format(j/60)
            df_total_duration.iloc[i, 1] = float(df_total_duration.iloc[i, 1])
        # sort by watchTime_min
        df_total_duration.sort_values(
            ['watchTime_min'], ascending=False, inplace=True)
        df_total_duration.reset_index(inplace=True, drop=True)

        # heatmap
        heatmap = df_yr.groupby('watch_time').size()
        heatmap_json = heatmap.to_json()

        # 频道观看次数
        df_chnlSize = pd.DataFrame(df_yr["channel_title"].value_counts())
        df_chnlSize.reset_index(inplace=True)
        # csv相关
        df_chnlSize.columns = ['channelTitle', 'watchTimes2']
        df_chnlSize.insert(2, 'channelLink', value='NaN')
        for i, j in df_chnlSize['channelTitle'].items():
            dictz = dict(
                df_yr.loc[df_yr['channel_title'] == j, 'channel_link'])
            chnlLink = dictz.get(int(next(iter(dictz))))
            df_chnlSize.loc[i, 'channelLink'] = chnlLink
        # dfz = pd.concat([df_cat, df_chnlSize, df_lang], axis=1)
        # dfz = dfz.fillna('')
        # print(df_cat)
        df_calc_times_json = df_calc_times.to_json(orient='records')
        df_calc_duration_json = df_total_duration.to_json(orient='records')
        # df_cat_json = df_cat.to_json()
        df_chnl_size_json = df_chnlSize.to_json(orient='records')
        df_lang_json = df_lang.to_json(orient='records')
        videos_words = df_yr['video_title'].tolist()
        comments_words = df_comments_yr['COMMENTS'].tolist()
        searches_words = df_searches_yr['SEARCHES'].tolist()
        return {
            # "video_detail": json.loads(df_json),
            # dfz_json,
            "topic": json.loads(df_calc_times_json),
            "category_duration_detail": json.loads(df_calc_duration_json),
            # df_cat_json,
            "channel": json.loads(df_chnl_size_json),
            "lang": json.loads(df_lang_json),

            "top5": json.loads(top5_json),
            # "year_detail": json.loads(df_yr_json),
            "stat": json.loads(dfstat_json),
            "heatmap": json.loads(heatmap_json),
            "wordcloud": {
                "videos": videos_words,
                "comments": comments_words,
                "searches": searches_words,
            },
            # "annual_video_detail": json.loads(df_yr_dlc_json),
            "duration": df_duration_json,
        }
        # csv相关


def id_name(id):
    return INDICT.get(id)

# 时间格式化函数


# 时间格式化函数
def time_format(str):
    num_list = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
    str = str.replace('Sept', 'Sep')
    if str[-5] == 'M' and str[0] not in num_list:
        str = str[:-4]
        date = datetime.datetime.strptime(str, "%b %d, %Y, %I:%M:%S %p")
        date_string = date.strftime("%Y-%m-%d %H:%M:%S")
        str = date_string

    elif str[-5] != 'M' and str[0] not in num_list:
        str = str[:-4]
        date = datetime.datetime.strptime(str, "%b %d %Y, %H:%M:%S")
        date_string = date.strftime("%Y-%m-%d %H:%M:%S")
        str = date_string

    elif str[-5] == 'M' and str[0] in num_list:
        str = str[:-4]
        date = datetime.datetime.strptime(str, "%d %b, %Y, %I:%M:%S %p")
        date_string = date.strftime("%Y-%m-%d %H:%M:%S")
        str = date_string

    elif str[-5] != 'M' and str[0] in num_list:
        str = str[:-4]
        date = datetime.datetime.strptime(str, "%d %b %Y, %H:%M:%S")
        date_string = date.strftime("%Y-%m-%d %H:%M:%S")
        str = date_string

    return str


# 处理&打开文件，
# where store the picture
# image_dir = os.path.join(os.getcwd(), "Images/")
# Youtube LOGO
# logo = os.path.join(image_dir, "LOGO.png")
# CSV File DIR
# csv_dir = os.getcwd()+'/csv_file/'
# if not os.path.exists(csv_dir):
#     os.mkdir(csv_dir)
