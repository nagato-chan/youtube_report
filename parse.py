#!/usr/bin/python3
import re
import os
import json
import datetime,pytz
import collections
import itertools
import shutil
import pandas as pd
import random
import itertools
import signal
import time




t1 = datetime.datetime.now()
print("start >> {}".format(t1))
year = str(time.strftime('%Y', time.localtime()))
month = str(time.strftime('%m', time.localtime()))
day = str(time.strftime('%d', time.localtime()))

missing=[]
dir = os.path.join(os.getcwd(),"Takeout/YouTube/")
if not os.path.exists(dir):
	missing.append(dir)
found=False
for path in ("Verlauf/Wiedergabeverlauf.html","history/watch-history.html"):	
	watch_history = os.path.join(dir,path)
	if os.path.exists(watch_history):
		found=True
		break
if not found:
	missing.append(watch_history)
found=False
for path in ("Verlauf/Suchverlauf.html","history/search-history.html"):	
	search_history = os.path.join(dir,path)
	if os.path.exists(search_history):
		found=True
		break
if not found:
	missing.append(search_history)
found=False
for path in ("Meine Kommentare/Meine Kommentare.html","my-comments/my-comments.html"):	
	comments_history = os.path.join(dir,path)
	if os.path.exists(comments_history):
		found=True
		break
if not found:
	missing.append(comments_history)
found=False
playlists_path = os.path.join(dir, 'playlists')
# os.startfile(playlists_path)
# src_filename = "Liked videos.csv"
# name, ext = os.path.splitext(src_filename)
# src_name = os.path.basename(name)
# dst_filename = src_name + '.json'
# shutil.copyfile(src_filename, dst_filename)
# print(f"File '{src_filename}' copied to '{dst_filename}' successfully.")
for path in ("Playlists/Positive Bewertungen.json","playlists/Liked videos.csv"):
	like_history = os.path.join(dir,path)
	if os.path.exists(like_history):
		found=True
		break
if not found:
	missing.append(like_history)
del found

if len(missing)>0:
	raise OSError("Required directories do not exist: %s"%(missing))
del missing


class HTML:
    with open(watch_history, "r", encoding="utf-8") as f:
        html_watch = f.read()
    with open(search_history, "r", encoding="utf-8") as f:
        html_search = f.read()
    try:
        with open(comments_history, "r", encoding="utf-8") as f:
            html_comment = f.read()
    except Exception:
       print("Could not parse comments.")

    def find_links(self):
        # search all links based on your personal html file
        links = []
        #if you want to understand ↓these↓, go to regex101.com.
        #also, I just assumed that the previously written english regex was faulty too, but replace that one if needed. I've only got the german one on hand.
        for translation in (r"""Watched\xa0<a href=\"([^\"]*)\">[^<]*<\/a>""",r"""<a href=\"([^\"]*)\">[^<]*<\/a>\xa0angesehen"""):
            links+=self.raw_find_links(translation)
        return links
    def find_video_id(self):
        # search all links based on your personal html file
        links = []
        #if you want to understand ↓these↓, go to regex101.com.
        #also, I just assumed that the previously written english regex was faulty too, but replace that one if needed. I've only got the german one on hand.
        for translation in (r"""v=([^\"]*)""",r"""<a href=\"([^\"]*)\">[^<]*<\/a>\xa0angesehen"""):
            links+=self.raw_find_links(translation)
        links2 = []
        for i in links:
            if '</a>' in i:
                p = re.compile(r"""(.*)<\/a>""")  # (.[^ <] *)
                j = p.findall(str(i))
                # return i
                # links2.append(j)
                # return j
            else:
                links2.append(i)
        return links2
    # 下面的watch history的title/time可与video_id一并写入一个函数，从而直接输出三列的df而无需在report中分别再处理它们
    def find_video_title(self):
        # search all links based on your personal html file
        links = []
        #if you want to understand ↓these↓, go to regex101.com.
        #also, I just assumed that the previously written english regex was faulty too, but replace that one if needed. I've only got the german one on hand.
        for translation in (r"""Watched\xa0<a href=\"[^\"]*\">([^<]*)<\/a>""",r"""<a href=\"([^\"]*)\">[^<]*<\/a>\xa0angesehen"""):
            links+=self.raw_find_links(translation)
        return links
    def find_date_time(self):
        # search all links based on your personal html file
        links = []
        # if you want to understand ↓these↓, go to regex101.com.
        # also, I just assumed that the previously written english regex was faulty too, but replace that one if needed. I've only got the german one on hand.
        for translation in (
        r"""<br>(\w{1,3}\s.[^"]*)<\/div>""", r"""<a href=\"([^\"]*)\">[^<]*<\/a>\xa0angesehen"""):#r"""v=([^"]*)""",
            links += self.raw_find_links(translation)
        return links
    def raw_find_links(self,translation):
        pattern = re.compile(translation)
        matchList = pattern.findall(str(self.html_watch))
        # save links into list
        return [match for match in matchList if type(match)==str]	#just sorting out stuff that could f up the whole script

    # heatmap_week
    # def find_times(self):
    #     times = []
    #
    #     for translation in ((
    #                         r"<\/a><br><a href=.*?<.*?<.*?>(.\w*\s.*?)<\/div>",
    #                         '%b %d %Y %I:%M:%S %p'),
    #                         (
    #                         r"<\/a><br><a href=.*?<.*?<.*?>(.\d*\s.*?)<\/div>",
    #                         '%d %b %Y %H:%M:%S')):
    #
    #     # for translation in (regex):
    #     # for translation in ((r"""<\/a><br><a href=.*?<.*?<.*?>([^<]*)<\/div>"""),
    #     #                     (r"<\/a><br><a href=.*?<.*?<.*?>([^<]*)<\/div>")):
    #         times+=self.raw_find_times(*translation)
    #     # return times
    def raw_find_times(self):
        regex0 = r"<\/a><br><a href=.*?<.*?<.*?>.*?<\/div>"
        regex1 = [r"<\/a><br><a href=.*?<.*?<.*?>([A-Z][a-z]{2,3}\s\d\d?.*?)<\/div>", '%b %d %Y %I:%M:%S %p']
        regex2 = [r"<\/a><br><a href=.*?<.*?<.*?>(\d\d?\s[A-Z][a-z]{2,3}.*?)<\/div>", '%d %b %Y %H:%M:%S']
        pattern0 = re.compile(regex0)
        pattern1 = re.compile(regex1[0])
        pattern2 = re.compile(regex2[0])
        raw_matchlist = pattern0.findall(str(self.html_watch))
        raw_matchlist_element = raw_matchlist[0]
        # return raw_matchlist_element
        is_regex1 = True
        testlist = pattern1.findall(str(raw_matchlist_element))
        # return matchList
        if len(testlist) != 0:
            matchList = pattern1.findall(str(raw_matchlist))
            times1 = []
            for time in matchList:
                if type(time) != str:
                    time = ' '.join(time)
                time = time.replace(',', '')
                time = time.replace('Sept', 'Sep')
                times1.append(time)
                # return times1
            times2 = []
            for i in times1:
                i = re.sub(r'.{3}$', 'UTC', i)
                i = i.split()
                tz = ''.join(i[-1])
                timez = ' '.join(i[:-1])
                # return tz
                if is_regex1:
                    date_time_time = datetime.datetime.strptime(timez, regex1[1])
                else:
                    date_time_time = datetime.datetime.strptime(timez, regex2[1])
                times2.append(pytz.timezone(tz).localize(date_time_time))
            # return is_regex1
            return times2
        else:
            is_regex1 = False
            matchList = pattern2.findall(str(raw_matchlist))
            times1 = []
            for time in matchList:
                if type(time) != str:
                    time = ' '.join(time)
                time = time.replace(',', '')
                time = time.replace('Sept', 'Sep')
                times1.append(time)
                # return times1
            times2 = []
            for i in times1:
                i = re.sub(r'.{3}$', 'UTC', i)
                i = i.split()
                tz = ''.join(i[-1])
                timez = ' '.join(i[:-1])
                # return tz
                if is_regex1:
                    date_time_time = datetime.datetime.strptime(timez, regex1[1])
                else:
                    date_time_time = datetime.datetime.strptime(timez, regex2[1])
                times2.append(pytz.timezone(tz).localize(date_time_time))
            # return is_regex1
            return times2





    # def _find_times(self):
    #     """
    #     Find and format times within the HTML file.
    #
    #     Returns
    #     -------
    #     times : List[str]
    #         e.g. "19 Feb 2013, 11:56:19 UTC Tue"
    #     """
    #     # Format all matched dates
    #     times = [
    #         datetime_obj.strftime("%d %b %Y, %H:%M:%S UTC %a")
    #         for datetime_obj in self._find_times_datetime()
    #     ]
    #     return times

    def search_history(self):
        search_raw = []
        search_clean = []
        pattern1 = re.compile(r"""Searched for\xa0<a href=\"(.*?\?search_query=.*?)\"\>(.*?)<\/a><br>(.*?)<""")
        raw_data = pattern1.findall(HTML.html_search)
        list = []
        for i in raw_data:
            # if '2022' in  i[2]:
                list.append(i)
        search_list = []
        search_link_list = []
        time_list = []
        for i in list:
            search_link_list.append(i[0])
            search_list.append(i[1])
            time_list.append(i[2])
        # return search_link_list
        df0 = pd.DataFrame(search_link_list)
        df1 = pd.DataFrame(search_list)
        df2 = pd.DataFrame(time_list)
        df_searches = pd.concat([df1,df0,df2], axis=1)
        df_searches.columns = ['SEARCHES','SEARCHES_LINK','DATE_TIME']

        # pattern2 = re.compile(r"search_query=[^%].*?>")
        # match_list = pattern2.findall(str(HTML.html_search))
        # # save links into list
        # for match in match_list:
        #     match = match[13:][:-2]
        #     match = match.split("+")
        #     search_raw.append(match)
        # search_raw1 = []
        # for i in search_raw:
        #     for j in i:
        #         search_raw1.append(j)
        # for word in search_raw1:
        #     if "%" not in word:
        #         search_clean.append(word)
        return df_searches
    def comment_history(self):
        try:
            # regex = r'(?<="\s+at\s+{yyyy}-{mm}-{dd}\s+{hh}:{mm}:{ss}\s+UTC\.\s+")\S+(?=")'
            # r"<a href=\".*\">[^<]*<\/a>\"([^\"]*)\"<br>"
            # r"<a href=\".*\">[^<]*<\/a>\"([^\"]*)\"<br>"
            pattern1 = re.compile(r"""<a href=['"].*?['"]>""")
            match_list1 = pattern1.findall(str(HTML.html_comment))
            pattern2 = re.compile(r"""at\s(.*?\s.[^\s]*).*?<br\/>(.*?)<\/li>""")
            match_list2 = pattern2.findall(str(HTML.html_comment))
            comments_list = []
            time_list = []
            for i in match_list2:
                time_list.append(i[0])
                comments_list.append(i[1])
            df1 = pd.DataFrame(comments_list)
            df2 = pd.DataFrame(time_list)
            df_comments = pd.concat([df1,df2],axis=1)
            df_comments.columns = ['COMMENTS','DATE_TIME']
            link = match_list1[-1][9:-2]
            return df_comments #match_list1, match_list2
        except Exception:
            pass
    def like_history(self):
            df_likes = pd.read_csv(playlists_path+'/'+ 'Liked videos.csv', encoding="utf_8_sig")
            # df = pd.DataFrame(f)
            df_likes.drop([0, 1], axis=0, inplace=True)
            df_likes.drop(df_likes.iloc[:, 2:], axis=1, inplace=True)
            # df.reset_index(inplace=True)
            df_likes.columns = ['liked_video_id','liked_time']
            df_likes.reset_index(inplace=True, drop=True)
            # print(df1.iloc[-1,0])
            # pattern = re.compile(r"videoId.{15}")
            # match_list = pattern.findall(str(data))
            # link = r"https://www.youtube.com/watch?v=" + match_list[-1][11:]
            df_link = df_likes[df_likes['liked_time'].str.contains('2022')]
            link = "https://www.youtube.com/watch?v=" + str(df_link.iloc[-1, 0])
            liked_video_url = []
            for i in df_likes['liked_video_id']:
                i = "https://www.youtube.com/watch?v=" + str(i)
                liked_video_url.append(i)
            df_likes['liked_video_url'] = liked_video_url
            liked_time = []
            for i in df_likes['liked_time']:
                i = i[:-4]
                liked_time.append(i)
            df_likes['liked_time'] = liked_time
            df_likes = df_likes.reindex(columns=["liked_video_id", 'liked_video_url', "liked_time"])
            return df_likes

    def dataframe_heatmap(self, day):
        times = self.raw_find_times()
        watchtimes=[0 for t in range(12)]
        
        for time in times:
        	if time.weekday()==day:
        		watchtimes[(time.hour//2)-time.hour%2]+=1

        return watchtimes

# a = HTML().comment_history()
# print(a)
# b = HTML().dataframe_heatmap()
# for time in b:
#     print(time.hour())
#     print(b)
# print(HTML().comment_history())
# print(len(HTML().comment_history()))

# cm = HTML().comment_history()
# list = []
# for i in cm:
#     # print(i)
#     # print()
#     pattern = re.compile(r"""<br\/>(.[^/<]*)""")
#     j = pattern.findall(i)
#     for k in j:
#         # print(k)
#         list.append(k)
#     # print(list)

# for i in range(500):
#     random_listelement = random.choice(list)
#     # print(random_listelement)
#     random_listelement_list = random_listelement.split(" ")
#     # print(random_listelement_list)
#     random_word = random.choice(random_listelement_list)
#     if random_word in stopwords:
#         random_word = random.choice(random_listelement_list)

# list = []
# for i in cm:
#     # print(i)
#     # print()
#     list.append(i)
# print(list)
# print(HTML().comment_history())
# print(HTML().find_date_time())
# print(HTML().search_history())
# print(HTML().find_links_title())
# print(HTML().find_date_time())
# print(HTML.html_search)
# print(HTML().like_history()[1])

print((HTML().html_watch))
# print(HTML().raw_find_times())

t2= datetime.datetime.now()
print("end >> {}".format(t2))
print("RUNTIME >> {}".format(t2-t1))