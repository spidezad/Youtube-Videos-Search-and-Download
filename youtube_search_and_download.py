"""
#############################################


 Author: Tan Kok Hua (Guohua tan)
 Revised date: Jul 16 2015

##############################################

 Usage:
     Search and Download the list of youtube videos/audio. Presently can only scan for playlist to download.
     
 Required:
     python pattern
     pafy -- for downloading youtube videos.

 Updates:
     Aug 01 2015: Include filter url portion
                  Enable sorting before download

 Learnings:

    https://developers.google.com/youtube/2.0/developers_guide_protocol_api_query_parameters
    http://www.makeuseof.com/tag/10-youtube-url-tricks-you-should-know-about/

    Identify item using firefox inspect element and copy the xpath
    dom_object('div h3 a') --> return the search results --> need to go individual to see more videos

    Age restriction handling
    http://digiwonk.wonderhowto.com/how-to/easiest-tricks-for-bypassing-youtubes-annoying-age-restrictions-nsfw-videos-0142999/

    Advanced search youtube
    https://support.google.com/youtube/answer/111997?hl=en

    xpath with text containing key phrases
    http://stackoverflow.com/questions/247135/using-xpath-to-search-text-containing

    youtube downloader -- pafy
    https://pypi.python.org/pypi/pafy
    http://pythonhosted.org/pafy/#
    https://pypi.python.org/pypi/pafy

    manual download of youtube videos
    http://stackoverflow.com/questions/2678051/can-t-download-youtube-video

    x-path for playlist
    //*[@id="item-section-600089"]/li[2]/div/div/div[2]/div[2]/ul/li/a

 ToDo:
    Search for individual songs instead of playlist
    able to download in chunks
    include sorting the links with the title
    split into playlist and non playlist type
    additional filter with leng limit

    read from file and multiple folder download according to keywords
    
    

"""

import re, os, sys, math
from pattern.web import URL, DOM, plaintext, extension
import pafy


class YouTubeHandler(object):
    """
        Class for constructing and parsing the url created from Youtube videos search and download.
        Currently, only target single page.
        
    """
    def __init__(self, search_keyword = '' ):
        """ Intializaton. Take in a seach keyword.
            Note currently handling only playlist type.
         
        """
        self.yt_search_key = search_keyword

        ##intialize
        #self.yt_downloader = pytube.YouTube()

        ## Users options
        self.retreive_fr_playlist = 1 # assume search for the playlist
        self.num_playlist_to_scan = 10 # get the number of playlist to scan.
        self.download_as_audio =1 # if 0 - download as video
        self.enable_sorted_download = 1 # 1 -enable sorted title before download
        
        ## url construct string text
        self.prefix_of_search_url = "https://www.youtube.com/results?search_query="
        self.target_yt_search_url_str = ''
        self.filter_url_portion = '&filters=playlist'#can add in different filter url portion, default set to playlist filter
    
        ## Intermediate outputs
        self.playlist_url_list = []#list of playlist url obtained from the search results.
        self.video_link_title_dict = {} #
        self.video_link_title_keylist = []#will be the list of dict key for the self.video_link_title_dict, for sorting purpose

        ## Storage
        self.video_download_folder = r'c:\data\temp\youtube_videos\\'
        
    def reformat_search_for_spaces(self):
        """
            Method call immediately at the initialization stages
            get rid of the spaces and replace by the "+"
            Use in search term. Eg: "Cookie fast" to "Cookie+fast"

            steps:
            strip any lagging spaces if present
            replace the self.yt_search_key
        """
        self.yt_search_key = self.yt_search_key.rstrip().replace(' ', '+')

    def form_search_url(self):
        """ Form the url from one selected key phrase.
            Set to self.target_yt_search_url_str
        """
        self.reformat_search_for_spaces()
        self.target_yt_search_url_str = self.prefix_of_search_url + self.yt_search_key + self.filter_url_portion 

    def get_dom_object(self, url_target):
        """ Get dom object based on element for scraping
            Take into consideration that there might be query problem.
            Args:
                url_target (str): url link to be searched.
            Returns:
                (DOM): dom object correspond to the url.
            
        """
        try:
            url = URL(url_target)
            dom_object = DOM(url.download(cached=True))
        except:
            print 'Problem retrieving data for this url: ', self.target_url_str
            self.url_query_timeout = 1

        return dom_object       

    def tag_element_results(self, dom_obj, tag_expr):
        """ Take in expression for dom tag expression.
            Args:
                dom_obj (dom object): May be a subset of full object.
                tag_expr (str): expression that scrape the tag object. Similar to xpath.
                                Use pattern css selector for parsing.
            Returns:
                (list): list of tag_element_objects.

            TODO: May need to check for empty list.
        """
        return dom_obj(tag_expr)

    def set_num_playlist_to_extract(self, num):
        """ Set the number of playlist to extract.
            Args:
                num (int): number of playlist to extract.
            Set to self.num_playlist_to_scan

        """
        self.num_playlist_to_scan = num

    def get_playlist_url_list(self):
        """ Get the list of playlist url list from the search page.
            Assume here is searching from a playlist of videos.
            set to self.playlist_url_list
        """
        #start with forming the search
        self.form_search_url()

        # Get the dom object from the search page
        search_result_dom = self.get_dom_object(self.target_yt_search_url_str)

        # Get the search playlist
        target_search_results_obj = self.tag_element_results(search_result_dom, 'div ul li a[class="yt-uix-sessionlink"]')

        playlist_link_results = []
        for n in target_search_results_obj:
            playlist_link_results.append(n.attributes['href'])

        playlist_link_results = [n for n in playlist_link_results if n.startswith('/playlist?')]
        self.playlist_url_list = ['https://www.youtube.com' + n for n in playlist_link_results]

    def get_all_video_link_fr_playlist(self, target_playlist_url):
        """ Get all the video url link and title from target_playlist.
            Args:
                target_playlist_url (str): target playlist url.
            Set to self.video_link_title_dict

        """
        py_dom_object = self.get_dom_object(target_playlist_url)
        py_results_obj =  self.tag_element_results(py_dom_object, 'tr td[class="pl-video-title"] a')

        each_video_link_title_dict = {}
        for n in py_results_obj:
            video_link = n.attributes['href']
            video_title = n.content.strip('\n [ ]')

            if video_link.startswith('/watch') and (video_title !='Private Video' and video_title !='Deleted Video'):
                # further process of data without the index
                video_link = re.search('(.*)\&list',video_link).group(1)
                #video_link = re.search('(.*)\&index',video_link).group(1)
                each_video_link_title_dict[video_title] = 'https://www.youtube.com' +video_link

        self.video_link_title_dict.update(each_video_link_title_dict)

    def get_video_link_fr_all_playlist(self):
        """ Get all video link from all the play list.
            The playlist limit is determined by the self.num_playlist_to_scan

        """
        for n in self.playlist_url_list[:self.num_playlist_to_scan]:
            print 'scanning playlist, ', n
            self.get_all_video_link_fr_playlist(n)

    def download_video(self,video_link, video_title):
        """ Download the video using pytube. Initialized self.yt_downloader.
            Args:
                video_link (str): video url link
                video_title (str): video title (may need to convert)
                try if can use the video title from downloader itself.
        """
        try:
            video = pafy.new(video_link)

            if not self.download_as_audio:

                selected_video_obj = video.getbest('mp4')
                if selected_video_obj == None:
                    selected_video_obj = video.getbest('flv')

                if selected_video_obj:
                    download_fullpath = os.path.join(self.video_download_folder, selected_video_obj.filename)
                    if not os.path.isfile(download_fullpath):
                        selected_video_obj.download(download_fullpath, quiet= True)

            else:
                bestaudio = video.getbestaudio()
                download_fullpath = os.path.join(self.video_download_folder, bestaudio.filename)
                if not os.path.isfile(download_fullpath):
                    bestaudio.download(download_fullpath, quiet= True)
        except:
            #print 'Have problem downloading this file', video_title
            print 'Have problem downloading this file'

    def sort_video_title(self):
        """ Sort the video according to title when download.
            Will sort across all playlist if more than one playlist are selected.
            Set to self.video_link_title_keylist
        """
        self.video_link_title_keylist = sorted(self.video_link_title_keylist)

    def download_all_videos(self, dl_limit =10):
        """ Download all video given in self.video_link_title_dict
            Will limit by dl_limit.
            Kwargs:
                dl_limit (int): set the limit of video download

        """
        counter = dl_limit
        self.video_link_title_keylist = self.video_link_title_dict.keys()

        if self.enable_sorted_download:
            self.sort_video_title()


        for title in self.video_link_title_keylist:
            #print 'downloading title: ', title
            print 'downloading title with counter: ', counter
            if not counter:
                return
            self.download_video(self.video_link_title_dict[title], title)
            counter = counter -1
    
def get_searchlist_fr_file(filename):
    """Get search list from filename. Ability to add in a lot of phrases.
        Will replace the self.g_search_key_list.
        Will ignore those that are commented, i.e, marked with '#'
        Args:
            filename (str): full file path
    """
    with open(filename,'r') as f:
        g_search_key_list = f.readlines()

    return [n for n in g_search_key_list if not n.startswith('#')]

                    
if __name__ == '__main__':

    """ 
        Selection.
        1 -- normal run
        2 -- check on pafy and also to download individual file based on url.

        Note: may not be very re
        
    """
    
    choice = 2

    if choice == 1:
        """

        """
        search_key = r'Tableau storyboard' #keywords
        yy = YouTubeHandler(search_key)
        yy.download_as_audio =0
        yy.enable_sorted_download = 0
        yy.set_num_playlist_to_extract(10)
        yy.get_playlist_url_list()
        #print yy.playlist_url_list
        #yy.playlist_url_list = yy.playlist_url_list[3:]

        yy.get_video_link_fr_all_playlist()
##        for key in  yy.video_link_title_dict.keys():
##            print key, '  ', yy.video_link_title_dict[key]
##            print
##        print
        print 'download video'
        yy.download_all_videos(dl_limit =5)

    if choice ==2:
        filename = r'c:\data\temp\youtube_searchlist.txt'
        keyword_list = get_searchlist_fr_file(filename)
        for search_key in keyword_list:
            yy = YouTubeHandler(search_key)
            yy.download_as_audio =0
            yy.enable_sorted_download = 0
            yy.set_num_playlist_to_extract(10)
            yy.get_playlist_url_list()
            #print yy.playlist_url_list
            #yy.playlist_url_list = yy.playlist_url_list[3:]

            yy.get_video_link_fr_all_playlist()
            print 'download video'
            yy.download_all_videos(dl_limit =5)

        

    if choice == 3:
        """
            For trying out the pafy or can be used to download individual songs.

        """
        sample_video_link = 'https://www.youtube.com/watch?v=u2PuH4WN9Zw&index=30'

        video = pafy.new(sample_video_link)
        print video.title

        use_audio = 0

        if not use_audio:

            selected_video_obj = video.getbest('mp4')
            if selected_video_obj == None:
                selected_video_obj = video.getbest('flv')

            if selected_video_obj:
                download_fullpath = os.path.join(r'c:\data\temp\youtube_videos',selected_video_obj.filename)
                if not os.path.isfile(download_fullpath):
                    selected_video_obj.download(download_fullpath, quiet= True)

        else:
            bestaudio = video.getbestaudio()
            download_fullpath = os.path.join(r'c:\data\temp\youtube_videos',bestaudio.filename)
            if not os.path.isfile(download_fullpath):
                bestaudio.download(download_fullpath, quiet= True)



















