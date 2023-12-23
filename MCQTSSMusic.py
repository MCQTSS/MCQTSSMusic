import base64
import os.path
import sys
import threading
import time
import json
import argparse
import requests
import hashlib
import random
import string
import re
import math
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from functools import partial


def hash33(t):
	e = 0
	for i in range(len(t)):
		e += (e << 5) + ord(t[i])
	return e & 2147483647


def bkn(skey):
	Salt = 5381
	key_len = len(skey)
	for i in range(key_len):
		Salt = (Salt + (Salt << 5)) + ord(skey[i])
	return str(Salt & 2147483647)


def random_str(str_len):
	population = string.ascii_letters + string.digits + string.digits
	if str_len <= 0:
		raise ValueError("str_len should be a positive integer.")
	return ''.join(random.choices(population, k=str_len))


def MCQTSS_qzjwb(text, start_str, end):
	start = text.find(start_str)
	if start >= 0:
		start += len(start_str)
		end = text.find(end, start)
		if end >= 0:
			return text[start:end].strip()


def arg():  # 处理传递的参数
	global play_info
	# 创建 ArgumentParser 对象
	parser = argparse.ArgumentParser(description='支持传入参数快速播放&搜索音乐')

	# 添加命令行参数
	parser.add_argument('-play', help='请传入音乐ID,如1905521(必须整数)')
	parser.add_argument('-search', help='请传入要搜索的内容')
	# 解析命令行参数
	args = parser.parse_args()

	# 获取传入参数的值并打印
	if args.play and args.search:
		try:
			play_info = [0, int(args.play), args.search]
		except ValueError:
			play_info = [2, args.search]
	elif args.play:
		try:
			play_info = [1, int(args.play)]
		except ValueError:
			play_info = [-1]
	elif args.search:
		play_info = [2, args.search]
	else:
		play_info = [-1]


class MCQTSSConfig:
	def __init__(self, name, value=None, path=None):
		self.name = name
		self.value = value
		self.path = path or os.path.abspath(os.path.join('./MCQTSS', 'config.json'))
		self.data = json.loads(open(self.path, 'r').read()) if os.path.exists(self.path) else {}

	@property
	def set(self):
		self.data[self.name] = self.value
		with open(self.path, 'w+') as file:
			file.write(json.dumps(self.data))
		return True

	@property
	def get(self):
		return self.data.get(self.name, None)


class QQ_Music:
	def __init__(self):
		self._headers = {
			'Accept': '*/*',
			'Accept-Encoding': 'gzip, deflate, br',
			'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
			'Referer': 'https://y.qq.com/',
			'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_3_1 like Mac OS X; zh-CN) AppleWebKit/537.51.1 ('
			              'KHTML, like Gecko) Mobile/17D50 UCBrowser/12.8.2.1268 Mobile AliApp(TUnionSDK/0.1.20.3) '
		}
		try:
			session = requests.Session()
			session.cookies.update(json.loads(open('./MCQTSS/cookie.json', 'r').read()))
			self._cookies = session.cookies
		except FileNotFoundError:
			self._cookies = {}

	def set_cookie(self, cookie):  # 网页Cookie转换到Python字典格式
		list_ret = {}
		cookie_list = cookie.split('; ')  # 分隔符
		for i in range(len(cookie_list)):
			list_1 = cookie_list[i].split('=')  # 分割等于后面的值
			list_ret[list_1[0]] = list_1[1]  # 加入字典
			if len(list_1) == 3:
				list_ret[list_1[0]] = list_1[1] + '=' + list_1[2]
		return list_ret

	def get_sign(self, data):  # QQMusic_Sign算法
		k1 = {"0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "A": 10, "B": 11, "C": 12,
		      "D": 13, "E": 14, "F": 15}
		l1 = [212, 45, 80, 68, 195, 163, 163, 203, 157, 220, 254, 91, 204, 79, 104, 6]
		t = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
		text = json.dumps(data, separators=(',', ':'))
		md5 = hashlib.md5(text.encode()).hexdigest().upper()
		t1 = ''.join([md5[i] for i in [21, 4, 9, 26, 16, 20, 27, 30]])
		t3 = ''.join([md5[i] for i in [18, 11, 3, 2, 1, 7, 6, 25]])

		ls2 = []
		for i in range(16):
			x1 = k1[md5[i * 2]]
			x2 = k1[md5[i * 2 + 1]]
			x3 = ((x1 * 16) ^ x2) ^ l1[i]
			ls2.append(x3)
		ls3 = []
		for i in range(6):
			if i == 5:
				ls3.append(t[ls2[-1] >> 2])
				ls3.append(t[(ls2[-1] & 3) << 4])
			else:
				x4 = ls2[i * 3] >> 2
				x5 = (ls2[i * 3 + 1] >> 4) ^ ((ls2[i * 3] & 3) << 4)
				x6 = (ls2[i * 3 + 2] >> 6) ^ ((ls2[i * 3 + 1] & 15) << 2)
				x7 = 63 & ls2[i * 3 + 2]
				ls3.extend(t[x4] + t[x5] + t[x6] + t[x7])

		t2 = ''.join(ls3).replace('[\\/+]', '')
		sign = 'zzb' + t1 + t2 + t3
		return sign.lower().replace('+', '').replace('/', '').replace('=', '')

	def get_music_url(self, music_mid):  # 通过Mid获取音乐播放URL
		uin = ''.join(random.sample('1234567890', 10))  # UIN基本不校验,长度10就行,如果请求正常这是你的QQ号
		data = {
			"req": {
				"module": "CDN.SrfCdnDispatchServer",
				"method": "GetCdnDispatch",
				"param": {
					"guid": "1535153710",
					"calltype": 0,
					"userip": ""
				}
			},
			"req_0": {
				"module": "vkey.GetVkeyServer",
				"method": "CgiGetVkey",
				"param": {
					"guid": "1535153710",
					"songmid": [music_mid],
					"songtype": [0],
					"uin": uin,
					"loginflag": 1,
					"platform": "20",
					# 'filename': [f'M500{music_mid}.mp3'],
				}
			},
			"comm": {
				"uin": uin,
				"format": "json",
				"ct": 24,
				"cv": 0
			}
		}
		ret = json.loads(requests.get('https://u.y.qq.com/cgi-bin/musicu.fcg?data={}'.format(json.dumps(data)),
		                              headers=self._headers, cookies=self._cookies).text)
		if ret['code'] == 500001:  # 如果返回500001表示提交的数据有问题或Cookie过期之类的(解析绿钻歌曲你不是绿钻也有可能给你这个)
			return 'Error'
		return 'https://dl.stream.qqmusic.qq.com/{}'.format(ret['req_0']['data']['midurlinfo'][0]['purl'])

	def get_music_info(self, music_id):  # 通过音乐的ID获取歌曲信息
		uin = ''.join(random.sample('1234567890', 10))
		data = {"comm": {"cv": 4747474, "ct": 24, "format": "json", "inCharset": "utf-8", "outCharset": "utf-8",
		                 "notice": 0, "platform": "yqq.json", "needNewCode": 1, "uin": uin,
		                 "g_tk_new_20200303": 708550273, "g_tk": 708550273},
		        "req_1": {"module": "music.trackInfo.UniformRuleCtrl", "method": "CgiGetTrackInfo",
		                  "param": {"ids": [music_id], "types": [0]}}}
		ret = json.loads(requests.get(url='https://u.y.qq.com/cgi-bin/musicu.fcg?data={}'.format(json.dumps(data)),
		                              headers=self._headers, cookies=self._cookies).text)
		if ret['code'] == 500001:  # 如果返回500001代表提交的数据有问题
			return 'Error'
		return ret['req_1']['data']['tracks']  # 直接返回QQ音乐服务器返回的结果,和搜索返回的感觉差不多,直接返回tracks数组\

	def get_album_info(self, album_mid):  # 获取专辑信息
		uin = ''.join(random.sample('1234567890', 10))  # 和音乐的那个一样,uin随机10个数字就行
		data = {"comm": {"cv": 4747474, "ct": 24, "format": "json", "inCharset": "utf-8", "outCharset": "utf-8",
		                 "notice": 0, "platform": "yqq.json", "needNewCode": 1, "uin": uin,
		                 "g_tk_new_20200303": 708550273, "g_tk": 708550273},
		        "req_1": {"module": "music.musichallAlbum.AlbumInfoServer", "method": "GetAlbumDetail",
		                  "param": {"albumMid": album_mid}}}
		resp = json.loads(requests.get(url='https://u.y.qq.com/cgi-bin/musicu.fcg?data={}'.format(json.dumps(data)),
		                               headers=self._headers, cookies=self._cookies).text)
		if resp['code'] == 500001:  # 如果返回500001代表提交的数据有问题
			return {'Error'}
		return resp

	def get_album_list(self, album_mid):  # 获取专辑信息
		resp = requests.get(
			url=f'https://i.y.qq.com/n2/m/share/details/album.html?ADTAG=ryqq.albumDetail&source=ydetail&albummid={album_mid}',
			headers=self._headers, cookies=self._cookies).text
		return json.loads(MCQTSS_qzjwb(resp, 'var firstPageData = ', '</script>'))['albumData']['list']

	def search_music(self, name, limit=20):  # 搜索歌曲,name歌曲名,limit返回数量
		return requests.get(url='https://shc.y.qq.com/soso/fcgi-bin/search_for_qq_cp?_=1657641526460&g_tk'
		                        '=1037878909&uin=1804681355&format=json&inCharset=utf-8&outCharset=utf-8&notice=0'
		                        '&platform=h5&needNewCode=1&w={}&zhidaqu=1&catZhida=1&t=0&flag=1&ie=utf-8&sem=1'
		                        '&aggr=0&perpage={}&n={}&p=1&remoteplace=txt.mqq.all'.format(name, limit, limit),
		                    headers=self._headers).json()['data']['song']['list']

	def search_music_2(self, name, limit=20):  # 搜索歌曲,name歌曲名,limit返回数量
		data = json.dumps(
			{"comm": {"g_tk": 997034911, "uin": ''.join(random.sample(string.digits, 10)), "format": "json",
			          "inCharset": "utf-8",
			          "outCharset": "utf-8", "notice": 0, "platform": "h5", "needNewCode": 1, "ct": 23, "cv": 0},
			 "req_0": {"method": "DoSearchForQQMusicDesktop", "module": "music.search.SearchCgiService",
			           "param": {"remoteplace": "txt.mqq.all",
			                     "searchid": "".join(random.sample(string.digits + string.digits, 18)),
			                     "search_type": 0,
			                     "query": name, "page_num": 1, "num_per_page": limit}}},
			ensure_ascii=False).encode('utf-8')
		return requests.post(
			url='https://u.y.qq.com/cgi-bin/musicu.fcg?_webcgikey=DoSearchForQQMusicDesktop&_={}'.format(
				int(round(time.time() * 1000))),
			headers={
				'Accept': '/',
				'Accept-Encoding': 'gzip, deflate, br',
				'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
				'Referer': 'https://y.qq.com/',
				'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_3_1 like Mac OS X; zh-CN) AppleWebKit/537.51.1 ('
				              'KHTML, like Gecko) Mobile/17D50 UCBrowser/12.8.2.1268 Mobile AliApp(TUnionSDK/0.1.20.3) '},
			data=data).json()['req_0']['data']['body']['song']['list']

	def get_playlist_info(self, playlist_id):  # 通过歌单ID获取歌单信息,songList返回的内容和搜索返回的差不多
		return json.loads(str(re.findall('window.__INITIAL_DATA__ =(.*?)</script>',
		                                 requests.get(url='https://y.qq.com/n/ryqq/playlist/{}'.format(playlist_id),
		                                              headers=self._headers,
		                                              cookies=self._cookies).text)[0]).replace('undefined',
		                                                                                       '"undefined"'))

	def get_playlist_info_num(self, playlist_id, song_num):  # 逐个获取歌单ID内容
		data = {"comm": {"g_tk": 5381, "uin": "", "format": "json", "inCharset": "utf-8", "outCharset": "utf-8",
		                 "notice": 0, "platform": "h5", "needNewCode": 1},
		        "req_0": {"module": "music.srfDissInfo.aiDissInfo", "method": "uniform_get_Dissinfo",
		                  "param": {"disstid": int(playlist_id), "enc_host_uin": "", "tag": 1, "userinfo": 1,
		                            "song_begin": song_num, "song_num": 10}}}
		resp = json.loads(requests.post(
			url='https://u.y.qq.com/cgi-bin/musicu.fcg?_webcgikey=uniform_get_Dissinfo&_={}'.format(
				int(time.time() * 1000)),
			headers=self._headers, cookies=self._cookies, data=json.dumps(data)).text)
		if resp['code'] == 500001:  # 如果返回500001代表提交的数据有问题
			return 'Error'
		return resp['req_0']['data']['songlist']

	def get_recommended_playlist(self):  # 获取QQ音乐推荐歌单,获取内容应该和Cookie有关
		return json.loads(str(re.findall('window.__INITIAL_DATA__ =(.*?)</script>',
		                                 requests.get(url='https://y.qq.com/n/ryqq/category',
		                                              headers=self._headers,
		                                              cookies=self._cookies).text)[0]).replace('undefined',
		                                                                                       '"undefined"'))

	def get_lyrics(self, mid, translate=False):  # 获取歌曲歌词信息
		resp = requests.get(
			url='https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg?_={}'
			    '&cv=4747474&ct=24&format=json&inCharset=utf-8&outCharset=utf-8&notice=0&platform=yqq.json'
			    '&needNewCode=1&g_tk=5381&songmid={}'.format(
				time.time(), mid),
			headers=self._headers, cookies=self._cookies).json()
		if translate:
			data = resp['trans']
			if data == '':
				data = resp['lyric']
		else:
			data = resp['lyric']
		return base64.b64decode(data).decode('utf-8')

	def get_lyrics_info(self, mid, trans):
		resp = requests.get(
			url='https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg?_={}'
			    '&cv=4747474&ct=24&format=json&inCharset=utf-8&outCharset=utf-8&notice=0&platform=yqq.json'
			    '&needNewCode=1&g_tk=5381&songmid={}'.format(
				time.time(), mid),
			headers=self._headers, cookies=self._cookies).json()
		if trans in ['0', None, 0]:
			return [base64.b64decode(resp['lyric']).decode('utf-8'), base64.b64decode(resp['lyric']).decode('utf-8')]
		trans = resp['trans']
		if trans != '':
			trans = base64.b64decode(resp['trans']).decode('utf-8')
		else:
			trans = base64.b64decode(resp['lyric']).decode('utf-8')
		return [base64.b64decode(resp['lyric']).decode('utf-8'), trans]

	def get_radio_info(self):  # 获取个性电台信息
		return json.loads(str(re.findall('window.__INITIAL_DATA__ =(.*?)</script>',
		                                 requests.get(url='https://y.qq.com/n/ryqq/radio',
		                                              headers=self._headers,
		                                              cookies=self._cookies).text)[0]).replace('undefined',
		                                                                                       '"undefined"'))

	def get_toplist_music(self):
		return json.loads(re.compile('firstPageData\\s=(.*?)\n').findall(
			requests.get(url='https://i.y.qq.com/n2/m/share/details/toplist.html?ADTAG=ryqq.toplist&type=0&id=4',
			             headers=self.headers).text)[0])

	def get_mv_url(self, vid):  # 获取MV信息,下载地址
		data = {"comm": {"ct": 6, "cv": 0, "g_tk": 1366999994, "uin": ''.join(random.sample('1234567890', 10)),
		                 "format": "json", "platform": "yqq"},
		        "mvInfo": {"module": "video.VideoDataServer", "method": "get_video_info_batch",
		                   "param": {"vidlist": [vid],
		                             "required": ["vid", "type", "sid", "cover_pic", "duration", "singers",
		                                          "new_switch_str", "video_pay", "hint", "code", "msg", "name", "desc",
		                                          "playcnt", "pubdate", "isfav", "fileid", "filesize", "pay",
		                                          "pay_info", "uploader_headurl", "uploader_nick", "uploader_uin",
		                                          "uploader_encuin"]}},
		        "mvUrl": {"module": "music.stream.MvUrlProxy", "method": "GetMvUrls",
		                  "param": {"vids": [vid], "request_type": 10003, "addrtype": 3, "format": 264}}}
		return requests.post(url='https://u.y.qq.com/cgi-bin/musicu.fcg', data=json.dumps(data), timeout=1,
		                     headers=self._headers).json()

	def get_singer_album_info(self, mid):
		uin = ''.join(random.sample('1234567890', 10))  # 和音乐的那个一样,uin随机10个数字就行
		data = {"req_0": {"module": "music.homepage.HomepageSrv", "method": "GetHomepageTabDetail",
		                  "param": {"uin": uin, "singerMid": mid, "tabId": "album", "page": 0,
		                            "pageSize": 10, "order": 0}},
		        "comm": {"g_tk": 1666686892, "uin": int(uin), "format": "json", "platform": "h5", "ct": 23}}
		resp = requests.get(url='https://u.y.qq.com/cgi-bin/musicu.fcg?data={}'.format(json.dumps(data)),
		                    headers=self._headers, cookies=self._cookies).json()
		if resp['code'] == 500001:  # 如果返回500001代表提交的数据有问题
			return 'Error'
		return resp['req_0']['data']['list']

	def get_Toplist_Info(self):
		data = {
			"comm": {
				"cv": 4747474,
				"ct": 24,
				"format": "json",
				"inCharset": "utf-8",
				"outCharset": "utf-8",
				"notice": 0,
				"platform": "yqq.json",
				"needNewCode": 1,
				"uin": 0,
				"g_tk_new_20200303": 5381,
				"g_tk": 5381
			},
			"req_1": {
				"module": "musicToplist.ToplistInfoServer",
				"method": "GetAll",
				"param": {}
			}
		}
		return requests.get(
			url='https://u.y.qq.com/cgi-bin/musics.fcg?_={}&sign={}'.format(int(time.time() * 1000),
			                                                                self.get_sign(data)),
			headers=self._headers, cookies=self._cookies, data=json.dumps(data, separators=(',', ':'))).json()['req_1']

	@property
	def headers(self):
		return self._headers


class Downloader:
	downloaded_bytes = 0
	file_size = 0
	start_time = 0

	def __init__(self, url, num_threads, proxy=None):
		self.url = url
		self.num_threads = num_threads
		self.session = requests.Session()
		self.error = {}
		self.download_error = False
		if proxy:
			self.session.proxies = {
				'http': 'socks5://' + proxy,
				'https': 'socks5://' + proxy,
			}
		try:
			os.makedirs('MCQTSS')
		except:
			pass

	def get_file_size(self):
		response = self.session.head(self.url, allow_redirects=True, verify=False)
		response.raise_for_status()
		return int(response.headers.get('Content-Length', 0))

	def download_part(self, start, end, part_number):
		headers = {
			'Range': 'bytes={}-{}'.format(start, end),
			'Accept-Encoding': '*',
		}
		try:
			response = self.session.get(self.url, headers=headers, stream=True, verify=False)
			response.raise_for_status()
			filename = './MCQTSS/{}.part_{}'.format(os.path.basename(self.url).split('?')[0], part_number)
			with open(filename, 'wb') as f:
				for chunk in response.iter_content(chunk_size=4096):
					f.write(chunk)
					self.downloaded_bytes += len(chunk)
					elapsed_time = time.time() - self.start_time
					speed = self.downloaded_bytes / elapsed_time
					if speed / 1024 / 1000 < 1:
						print('\r{:.2f}%  {:.2f} KB/s'.format(
							100 * self.downloaded_bytes / self.file_size,
							speed / 1024,
						), end='')
					else:
						print('\r{:.2f}%  {:.2f} MB/s'.format(
							100 * self.downloaded_bytes / self.file_size,
							speed / 1024 / 1000,
						), end='')
		except Exception as e:
			try:
				error_code = self.error[str(part_number)]
			except Exception:
				self.error[str(part_number)] = 0
				error_code = 0
			error_code += 1
			self.error[str(part_number)] = error_code
			if error_code > 5:
				self.download_error = True
				return 'Error'
			print('块:{}下载出错,正在重试\b{}'.format(part_number, e))
			self.download_part(start, end, part_number)
			return

	def download(self):
		print(self.url)
		self.file_size = self.get_file_size()
		self.start_time = time.time()
		part = math.ceil(self.file_size / self.num_threads)
		threads = []
		for i in range(self.num_threads):
			start = part * i
			end = min(self.file_size, start + part) - 1
			t = threading.Thread(target=self.download_part, args=(start, end, i + 1))
			t.start()
			threads.append(t)
		for t in threads:
			t.join()
		if self.download_error:
			return 'Error'
		with open('./MCQTSS/' + os.path.basename(self.url).split('?')[0], 'wb') as f:
			for i in range(self.num_threads):
				with open('./MCQTSS/{}.part_{}'.format(os.path.basename(self.url).split('?')[0], i + 1), 'rb') as part:
					f.write(part.read())
		for i in range(self.num_threads):
			os.remove('./MCQTSS/{}.part_{}'.format(os.path.basename(self.url).split('?')[0], i + 1))
		return './MCQTSS/' + os.path.basename(self.url).split('?')[0]


class MCQTSS_resource:
	def __init__(self):
		self.img_play = "data:application/octet-stream;base64,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"
		self.img_stop = 'data:application/octet-stream;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAYAAACtWK6eAAAAAXNSR0IArs4c6QAAHotJREFUeF7tXQ1wZUWVPufl571BHIQdEKxyWTSbqbzbN5kQBQVqFVTEwR9wS4VSkRIYEFiUkR//8A9FHWAQFhCRsWZFS9BaB10d0UVAC1DQMJPcvi81McqyVAnKLCgC8/Lz7tk68YYKcTKvu+/P63dfd9Wrl0pOd5/++nzpv9OnEVxyCDgElkUAHTYOAYfA8gg4gjjrcAjsAQFHEGceDgFHEGcDDgEzBNwIYoaby9UhCDiCdEhHu2aaIeAIYoaby9UhCDiCdEhHu2aaIeAIYoaby9UhCDiCdEhHu2aaIeAIYoabcq7h4eH9Z2dnPSKqAsBLEXElAKzkbyKa/xkA9om/+WdOT8Wfv/A3Ij5FRPO/i78fQcRaT09PuG3btseVlXGC2gg4gmhDtvsMi4mAiB4AMCH4e/+UqliuGCZICAA1IgodcdJF2xHEEE8hxCARHYaI/wIA/DnYsKissj0MAL8gol8g4gNSyvGsKipyuY4gCr27evXqF3Z3d78CAF6JiPzNhHixQlabRP4YE+Y3APDrubm53+zYseOvNilooy6OIHvoFd/31wLACVEUnYiIq2zsQFOdiGhnqVTaAgC3BUGw1bScoudzBFnSw57nDSHiCQBwIgAMFd0A4vaNAcAWIrotDEP+2aUYAUcQAOjv71/V09PDowQTg0eNTk5bmSizs7NbJicnd3YyENz2jibIwMDAwd3d3acT0WkAcFCnG8OS9j+KiJvm5uZumpiY4AV/R6aOJMjQ0FB/FEWnEdHpALBfR/a8eqOfQMSbSqXSprGxsUn1bMWQ7CiC+L7vx6MFjxh7F6MLc2vF0wCwiUeVIAiC3GptcUUdQZBqtTpcKpXWAQATo6fFmLd79bNMlCiKbqzVatvavTHN9C80QUZGRvaanp6+EAAuAoC9moGR4d/nAGAi/vCJdx0RdyFinYie9806EFEFEVcs/iaiFYhYiU/oBwCAP90Z6tys6GcBYEO5XL58dHSUfy5kKixBPM87iYmBiMN59hwi8n9VPrWeiKJo/jMxMfHbLHQYGBj451KpNMCfmDB8up9re4mI27shDMNbsmhjq8ssHEHi6RSPGEyQrNMMIt4TRdG9AHDv9PT0L6emptipsGWpr69vZblcfjUAHFkqlY4koqMAoDcHhW6JomhD0aZdhSFIjtMpHh2+R0S/soEQzQx/gTCI+CoAeDsADDbLk+DvhZt2FYIgnucdAwBXZDidepJPmvkjpfxhAgNqeVYhxJtjLwH2FNg3C4XiadcFYRjemUX5eZbZ9gTxPO8cRLwqo92pO3i0iKJoS61WeyzPjsm6rmq1emCpVGKS8Kjy+gzqmyWi88MwvC6DsnMrsm0JMjIy0lOv169CxHNSRusZItpMRN+o1WoPpFy2lcVVq1V22z8FEU8FgBekqSQRXVepVM4fHR3l7eG2S21JEL6LwaMGEfHUKpWEiH9gYjQajc1Z7TqlomiGhfCuWFdX16lMFCJ6SVpVIeKdPJq0452UtiOIEOJdiLgxxQ6cYGJ0dXVtHh8f/1NaRtHO5QwODh7QaDTmiRJvHyduTvwPaL2U8tbEheVYQFsRRAjxKQD4dEr41BDxml27dm2empqaTqnMQhXT19dXXrFiBY8m58UHlGm079NSys+kUVAeZbQNQYQQvNg7OwVQeI1xZaVS2Tg6OspBEVxqgsDIyMg+9Xp9PSJ+OKU1yvVSyrTXjpn0Y1sQRAjxHQB4R1IEEPE/iGhjO86Fk7Y9jfzx2m89Eb0vhfK+K6V8ZwrlZFqE9QQRQtwFAK9NiAKXwcRo6zOMhBiklj0+S1kPAEcnLPRuKWXSMhKqsOfsVhPE931JRBw6J0m6UEp5RZICXN7dIyCEuAAALk+CDyKGQRCIJGVkmddagggheEcpSUwpdglhcvw0SwA7vWwhxLExSZK4sDwupTzARiytJIgQghKCdXNMDg5141LGCAghOAQSjyTvTVKVlNI6e7ROISHE7wHgkARAuylVAvCSZE1hyvWQlPJlSXRIO69VBBFCsHOb0aKN57JExAdRbkqVtpVolMdTrvgg13TteJeUMjUPCQ3VdytqDUGEEJsA4P2GDRotlUrvHh8f32GY32VLEYHBwcHVURR9CwBGDIv9upSSr0e3PFlBEM/zrkRE3jY0SfeVy+W17tDPBLrs8vDh4vT0NEdsPMKkFj6vCsOQDyZbmlpOECHEZQDwURMU2AkuCILXmeR1efJBwPf9nyVwKv2ClPJj+Wi6+1paSpCEvlVbpZTHtxI8V7caAkKIHyWIWNlS362WEYS9cgHA9KL/NVLKD6p1j5OyAQEhxNUAwE6PJumkVnkBt4QgsU/Pjw1d1i+TUn7cBGWXp7UICCE+DwDaU6bYVf5NrfChy50gfBNwZmbmdsN56dVSyg+1tptd7UkQEEJ8GQC0R39eb/b29h6X983E3Anied61htdkN0kpOZauS22OgBDipjjKpVZL+PpuGIbnamVKKJwrQeIAC9ca6HyLlPJkg3wui6UICCG+bRK7jIjOzTMQRG4E4dA8iHi7QfSRO8rl8tuKHN7SUhvOVK04jtn3DSKqcLSU4/IKKZQLQRiMer1+j0HcKlkqld46Pj7+UKa95QpvCQKDg4OHRFH0AwDQcnfnuFuVSuWoPP5p5kKQBOcdb3S+VS2x3dwqjd3lf2JQYS7nI5kTJI6Ve49BdHXnlWtgNe2YxdAL+Nkoio7KOhZw5gQxXIzdLKU8pR072+lshoAQ4hsG90ky37zJlCD8BAEi8m6FTuKbgMdKKd1lJx3U2lw2vnTFVxW0biYS0clZPr2QGUESLMzduqPNjd1UfZP1SNYL9swIYrgwd+sOU+sqSD7D9UhmC/ZMCGK4MLfqJllB7K0tm2FwszSzBXsmBBFCfAUAztLsnbe4uFWaiBVUPI679V+azbtBSvkBzTxNxVMnSPzU8qjOiTlHPAyCgAMlu+QQmEfA931+gkInguMsIo6k/UR16gQx8NZ8hq9ltsKV2dmivQjwlQgAuE8zFnDq3t6pEmRoaKi/0Wjw6LG3KvRE9NkwDDlqu0sOgech4HneZxDxkxqwPN3V1TUyNjY2qZFnj6KpEsT3/S8REb8wq5pq5XL5CBdwQRWuzpKLAz/wKFJVbTkibgiC4GJV+WZyqRFkYGDg4K6urgcBYL9mlS78HRHPCoLgq6ryTq7zEPB9/0wiukGj5U80Go1DJyYmHtbIs6xoagTxff9SIvqEhlIT9Xp92D1eo4FYB4ryIz6VSmWbzktXiPi5IAguSQOuVAjS39+/qre3l11EDlJVioguDsNwg6q8k+tcBDzPuwgRv6SBwKMzMzODk5OTOzXy7FY0FYJ4nncGIt6oqgxfwue7IUV5E5AjCXLbbYnsaJs+qnaxnBy/mcguJTpBPohoXRiGX0tadyoEMYh71PaRSTzP42eT18XOdS+MO+KvzBNEvDoIgu8m7Ryd/L7vv4OIOBgCb48+Tx8iujEMQ/aWbdtkEBEllbhpiQnied4QIm7XQP6ZRqMx3M5PLau48BPRR8Iw1JkWaED4fFHP8y5GxC82KSBz13DjBihkjJ+o5rWI8jvuRLQmDMMxheKzW6TrOiW2IjJFEoCW5vU873REVBq6EfEVQRDwuVBmyff9ESL6jUoFRHRGGIYcUaQtk0FEnMROjIlHECEEjx5DqohHUXR4rVZ7QFXeJrnBwcFXRVH0S1WdEPH+3t7eY7K6O81XCmZmZu4kosNVdSqVSq8eHx//laq8TXLVavWwUql0v4ZOY1LKNRryfyeaiCC+768lIo67qprukFK+QVXYNjnP874arzt0VDtPSvnvOhlUZYUQ/wYA16jKs1y8HjlTJ49NskKI/9aJhIKIxwdBwFHmjVJSgtzIw7ZGzWdLKdnTty2TEIKnMlpvXhDRj8MwXJtFgz3P24qIb9Ise1RK+QrNPNaICyHYY/d6VYV4OhwEAW+mGCVjgvT19a0sl8u/Q8RVijU/GUVRtVarPaYob52Y6duJWb29Z5s+eXRYtVo9sFQq1QBgX5X6iGjn9PT0y6empp5SkV8qY0wQIQRPlXSeO7Pm1SAToDiPbQZpmz6muOrmM3iNjGMc8NRMOxkTxPO8TyDipRo1tv2FKNsM0jZ9NGwhkajuhSoiuiQMw8+ZVGpMECEE3/h6s2Kl41JK5Z0uxTJzF7PNIG3TJ88OEULw+YZqBJQfSinfYqJfEoL8CQD2V6w08X60Yj2ZitlmkLbpkyn4SwrXPH97XEp5gIl+RgTROZxipZJutZk0LIs8thmkbfpkgflyZeoeMZge2hoRRHP/faa7u/vF27dv/3OeAGZRl20GaZs+WWC+XJlr1qx50dzcHAcX7FWs1+g8ypQg/LYgvzGoku6VUh6lImi7jG0GaZs+efefEIJjPh+pWO+tUsqTFGWfEzMlyP8CwEtVKkPELwdBcL6KrO0ythmkbfrk3X++719FRKpP8j0ipfxHXR21CTI8PLz/7OwsL9CVEiKeGATBbUrClgvZZpC26ZN39/m+fwIRbVGtt6en54Bt27Y9rirPctoEEUK8FgDuUq2ku7t73yKsP7i9thmkbfqo2kRacvE65EmN8o6WUt6tIa9PEM/zzkbE6xQr2S6lHFaUtV7MNoO0TZ9WdKAQgu+IKHnsEtE5YRgq+3GZjiBMjrNVwChaxETbDNI2fVRsIm0ZzQiM10spz9HRwWSKxdMrnmY1TYj4kSAIcrlV11SZFARsM0jb9EkBYu0ifN+/mIia3aZcKPduKeXROpWYEET5BJ2I3haGIT/SWIhkm0Hapk8rOtnzvLciIr+Wq5K0T9S1CKK7g9VoNPrb+e75UsRtM0jb9FGx0LRl4rvqyqFGdXeytAiiuYM1J6XsSRuQVpZnm0Hapk+r+kYIMQsA3Yr1a+1kaRFEcwcrkFKqelsqtq21YrYZpG36tKp3hBActNBXqV93J0uXIF/ghbeKIgDwHSmlqjuKYpGtFbPNIG3Tp1W9I4S4FQDeqVI/L+jDMPyoiizLaBFECKG8xQsAhXBxXwykbQZpmz6qRpe2nKbru9ZWry5BbgaA96g0MM/AaSr6pCFjm0Hapk8aGJuUoRg4b6Hob0op36tajxZBfN//PhG9VbHwD0optULSKJbbMjHbDNI2fVrVMUKI8wDgapX6EfEHQRC8TUXWZIqlc0h4ZhAEygGtVRVupZxtBmmbPq3qG9/31xGR6jszWoeFWiOIEILDaB6qCMQpUkqekhUm2WaQtunTqo4WQvCUSTU494NSSuXYZroEmQKAl6sAgYjvzDvCuYpeSWRsM0jb9EmCbZK8cWT77yiW8TspZZ+irPYulrKbCQC0fZifpSDaZpC26aNqdGnLaYYB0nI30R1B6gBQVmkgIr4hCII7VGTbRcY2g7RNn1b1o+/7ryci1cBw01LKiqqujiCqSLkLUxpI5StqE0HcFMug711sXgPQNLLYNMVyi3SNjlsQdQQxAE0ji02LdLfNq9FxjiAGYBlksWmb1x0UGnSgG0EMQNPIYs1BoXM1EaTRb8+JOoKYoKaexyZXE+esqN5vjiAGWJlkscZZ0bm7uxHExICzzmONu7vnee7ClEFvuymWAWgaWay5MOWu3LoRRMNucxO15sqtC9rgCJKb1WtUZE3QBhf2xxFEw25zEbUq7A+3WAih7G7iAsf9zUbcGiQ7rlgVOC4miM5hoQs96giSHTs41o+FoUeVI5u44NVuBMmUHX8jyGYiep9iPVoRTbhMLXd3zqCzk4WI24IgUL2iq9jG1onZdv/CNn1a0TO+7z9IREpPbOgGjTMiiOZOFtTr9X2mpqaeagV4addpm0Hapk/aeDcrr6+vb2WlUvlLM7lFf9cKO2pEEN2dLCI6LgzDn2g0wlpR2wzSNn3y7jjP896IiLer1qsbuNqIIPFC/X8A4GAVxYjo0jAMP6kia7uMbQZpmz5595/neZ9FxEsU631YSvlPirLPiWmvQWKCcIgVpeh0iHhnEASv01XMRnnbDNI2ffLuM9/3f0ZExyjWe7OU8hRF2WQE8TzvdET8mmJlM/V6ff8irENsM0jb9FG0h1TE4vUHv1jbq1IgEZ0RhuFNKrKLZUxHEH7WYEy1sqKsQ2wzSNv0UbWHNOR01x8AMCSl5GcStJIRQeJp1mMA8GLF2goR6d02g7RNH0VbSEVM08X9j1LKA00qTkIQjmT3DsVKx6WUQ4qy1orZZpC26ZNnxwkheAaj+kDTd6WUSu+HLG2DMUE8z7sIEXVesG37SIu2GaRt+uRFEM0wP0BEF4dhuMFEvyQEOZp3qDQq/bqU8jQNeetEbTNI2/TJq8OEEJsA4P2q9fFOVxiG7EOonYwJsnr16hd2d3f/HhFXKdb6ZBRF1VqtxmuXtky2GaRt+uTRqdVq9cBSqVQDgH1V6iOinXNzcy/bsWPHX1XkU5ticUG+79/I22caFZ8tpfyKhrxVokKI+wDg1ZpKGc9/m9UjhNBZBy4U90sp5RHNyrb170KIDwDA9ar68XFEEATrVOXTJshaIvqRRuV3SCnfoCFvlahm0Ip53RExs4eENONBLWCp7dFqUycIIThI9etVdULE44Mg2KoqnypBuDAhxHbeY1ZVIIqiw2u12gOq8jbJeZ53HCL+WEOnh7q7uw/dvn37nzXyKIuuWbPmRXNzcw8CwCGqmYjoTWEYKvsvqZabh1y1Wj2sVCrdr1HXmJRyjYb834kar0EWStLcj+YdhevCMDw3idKtzCuE4CniWSo6IOKJQRDcpiJrKuP7/glEtEUx/w1SSp6itGXyPO9aRDxHQ/nE52+JCeJ53hAi8iiimp5pNBrDExMTv1XNYJuc7/tfIqKL9qQXIr4nCIJv5aG77/vvJqJvNtFnQxAEF+ehTxZ1xHfPtwHAC1TLJ6I1YRgqe3zsrtzEBOFChRC8DlmrqjgAXCal/LiGvHWinucdg4iXxodVe8cK/h8A/LzRaKyfmJh4OE+lBwYGDu7q6toIAK8BgH+I634aAMaJ6JIwDHW25PNUXakuIcTnAeBjSsJ/E9oqpTxeQ363oqkQxPO8MxBR+UVbRPwDIg6Pj49zAIi2T57nVRGRpJQTNjRGCDFARBiGIW+Htn0aHBw8gIi2EdFLVBtDROvCMFR1qF222FQI0t/fv6q3t5cdwQ7SaIDx6aZqHU6uGAgYeG08OjMzMzg5ObkzKQKpEISV8H3/UiL6hIZCE/V6fXhqampaI48T7TAE+vr6ypVKhdceA6pNR8TPBUGgepFqj8WmRpB4DsxbjvtpNOSsIAhUH4BXLdbJFQgB3/fPJKIbNJr0RKPRODStNWBqBIlHkaa7O0saWiuXy0eMjo7qXLzXwMqJtjMCIyMj+0xPT7P3QlW1HYiY6m5dqgQZGhrqbzQa/Ezbwq5O03YR0WfDMPxUU0En0HEIeJ73GUTUiWfwdFdX18jY2NhkWmClShBWSgjxZQD4oIaCzwDAESa3vTTqcKJthoAQgu968OihfO4BAFdLKT+UZlNTJ4jv+z4R8SjSo6po0SIwqrbbyS2PgGbERC5oFhFHgiAI0sQ1dYLEo4iyO8aixrT9hao0O6aTy9K9EBVjlYkbTSYEqVarw6VS6R4A2Eujo++SUqqGcNEo1om2GwJCCD71P1pD72ejKDqqVqvxdnCqKROCxKMIL7w/ranthVLKKzTzOPECISCEuAAALtdsUmKnxOXqy4wgIyMje9Xr9XvYpUSzsW+UUv5UM48TLwACQohjAUArTC27oFQqlaNGR0efzQKCzAjCynqedxIifltTcXZZOVZK+UfNfE68jREQQnAIKf7HqBqpZL61RHRyGIa3ZNX0TAkST7WYICdpNsAoTKRmHU7cIgSEEMrhbBepfYuU8uQsm5E5QQwX7Nxmtx7JsuctKttw3ZHZwnwxNJkTJMGCnbO69YhFhpyFKibrjliPzBbmuRPEdMGOiCEi/uv4+PiOLDrHldlaBAYHB1cT0X8SkaejSdYL89wJEi/Y+QYeBwtQPmGPFR0tl8uvcw6NOiZkv2zsiPgzABjR1HY2Doaeyw3JXKZYCwB4nncOIl6rCQiL3yelPNIgn8tiKQJCiHvZB09XPSI6NwxDfkg2l5QrQeKRRDcyxTwQRXqIJ5eetbgSzYdvnmtJKyLi5E6QkZGRnpmZmds1XgZa3NWpXMS32HYKr5pBgI/n/kH29vYeNzo6OpsnSLkThBvHrswcgE3nEv4iUK6RUuq40+eJp6trDwgIIa4GgPN0QeIgHxzwrhVXIlpCkJgk7wIA0xPQtg8bpGsk7S5vELZncZNPklLe2goMWkaQmCQmDo0LOKV+OaYVHdAJdRpcolsMSy7nHcv1Q0sJEpOEdyTONjSUTVLK0w3zumw5ICCE4IczTd+FaXmg7ZYTJCaJSRj/he69pVwun5aVN2cONlTIKvhweHp6mh+60fXDW8Ajs2cjdAC3giAxSfgFoNfqKL9I9o5SqbRufHz8IcP8LluKCAwODh4SRRFH2lR+pmBJ9XdLKXUuTKWo/fOLsoYgrJbv+1LX7WBRcyQAfNjdJcnMVpQKjn2rruTNSqUMS4TYvSgIAqO8JvU1y2MVQeKRhOP17t9M8T383XkBJwAvSVZDr9zFVT4upTwgiQ5p57WOIDFJKGFDb47d5d2lq4RAqmSPLzvxNdn3qsgvJyOltM4erVNoATwhxO91Xk7aDeh8M5FHE3d9N4nVNskbT6mYHFo3AZcU+5CU8mUZqmlctLUEiUcS3egWuwPCTbmMzWPPGVOYUnEFVkezsZogMUm03sRepkt5h2yjlPKHGdlKRxUbx61arxmaZ3cYfV1KaXpGkgvm1hOEUfA870pE5A5JlDiCIxExUXj65ZImArEP3Xoiep9m1r8T534Iw/DDScvJOn9bECQeSS4DgI+mAMgzRHRlpVLZ6C5hqaHJl5vq9fp6RGSD1omVu1wFX5BS6jynpqZoBlJtQ5CYJEl8t5bCV0PEa3bt2rXZPeKze8vix2tWrFhxKhGxB67yEwRN7LSlvlW6HGorgsQkeRcibjR0ld8dPhNEtLmrq2tzUd5M1DWCpfL8JmCj0TgVEU/VedlpT/XGLuvrW+WVa4pJ2xEkJgnfJ7nK8NLVbrGKO3Bzo9HY3M5PVJsaAueLn1qeJ0aK/4Dmb4MS0fntuPZrS4JwZ/LNxHq9fpXmw/Iq9sNrlM1E9I1arfaASoZ2l6lWq4ch4inxiJHGGuM5SPiabKVSOT/vm4Bp9UnbEmQBgDgQxFUG0VJUMLwDAL4XRdGWWq32mEqGdpGpVqsHlkqlEwHg7QmcCvfUXI4+cn6eARaywL7tCcKgeJ7HzyZcYRAoWxXTJwFgC3/a/SwlPsNgYvBnX1UAdOQ4bhUAXBCGYS6heXR005UtBEHiKRffP7gQAC7SfJdEFzM+Q/keIv66q6vrvu3bt/9Zt4A85desWfOiRqNxBBG9Mh4tkriENFOdI6xvKJfLlxflfk5hCLLQc3EsYCaJ6UWdZkaw+O8zAPBrJgsA/Lyrq+vuVhMmJgTfq3lNTAomRq9Oowxlb4miaEMWj9gY6pNKtsIRZNHahAlyUYbTruU6YDsijgHARBRF85+sdsV416lUKg3whzehiGgIANakYhmKhcTTqQ1ZPkGgqEomYoUlSM7TrmadM8eEiT81Iqoj4i5ErBPR8765ICKqIOKKxd9EtAIRK/GB3TwhAKC7WcUZ/r1w06ndYVVogiyZdq2LgwfoxgbO0MbasmgO3LaJr9QWbTrVsQRZaHj8RDV7j/Jn77Y0z9Yp/TQTAxE3pf3Ucuua1LzmjhhBlsIwNDTUH0XRaUTEIYP2aw5TR0s8gYg3lUqlTWNjY5OdhkRHEmShkwcGBg7u7u4+nYh4RDmo0zq/SXsf5dFibm7upomJiYc7FZuOJshCp/f396/q6ek5ERFPAIC1nWoMcbu3EtFts7OzWyYnJ3d2OBbgCLLEAjzPG4qJwifNvG3aCYm3pbcwMcIw5J9dihFwBNmDKfi+z6PJCVEU8eiyqkhWQ0Q7S6USu8/cFgTB1iK1Lc22OIIooNnX17eyUqkcTkSHI+LhAMCfJLG7FGpNXeRxALifiO5HxPvr9fr9U1NTT6VeS8EKdAQx7FDf90eIiJ8Q46fh+PulhkVlle0RfroOAO5FxPuCIBjNqqIil+sIklLvDg8P7z87O+sRURUR+dVWvqLK31mPNDwyhADAJ/T8KnCtp6cn3LZtG//epYQIOIIkBLBZ9sXE4VEGEVcCwEr+JqL5nwFgn/ibf+bEUx/+/IW/EfEpIpr/Xfz9iCNCM+TT+bsjSDo4ulIKioAjSEE71jUrHQQcQdLB0ZVSUAQcQQrasa5Z6SDgCJIOjq6UgiLgCFLQjnXNSgcBR5B0cHSlFBQBR5CCdqxrVjoIOIKkg6MrpaAIOIIUtGNds9JBwBEkHRxdKQVF4P8BSSfyfd6jHawAAAAASUVORK5CYII='


class Ui_Form_Main(object):
	def setupUi(self, Form_Main):
		if not Form_Main.objectName():
			Form_Main.setObjectName(u"Form_Main")
		Form_Main.resize(430, 600)
		self.label_title = QLabel(Form_Main)
		self.label_title.setObjectName(u"label_title")
		self.label_title.setGeometry(QRect(10, 5, 171, 31))
		font = QFont()
		font.setFamily(u"\u5fae\u8f6f\u96c5\u9ed1")
		self.label_title.setFont(font)
		self.label_ver = QLabel(Form_Main)
		self.label_ver.setObjectName(u"label_ver")
		self.label_ver.setGeometry(QRect(173, 18, 131, 16))
		self.label_ver.setFont(font)
		self.label_close = QLabel(Form_Main)
		self.label_close.setObjectName(u"label_close")
		self.label_close.setGeometry(QRect(400, 8, 20, 20))
		self.label_partition_1 = QLabel(Form_Main)
		self.label_partition_1.setObjectName(u"label_partition_1")
		self.label_partition_1.setGeometry(QRect(10, 40, 411, 2))
		self.label_partition_1.setStyleSheet(u"background-color: #000;")
		self.tabWidget_main = QTabWidget(Form_Main)
		self.tabWidget_main.setObjectName(u"tabWidget_main")
		self.tabWidget_main.setGeometry(QRect(10, 30, 411, 501))
		self.tabWidget_main.setFont(font)
		self.tabWidget_main.setFocusPolicy(Qt.TabFocus)
		self.tabWidget_main.setStyleSheet(
			u"/* \u9690\u85cfQTabWidget\u7684\u8fb9\u6846\u5e76\u8bbe\u7f6e\u4e3a\u900f\u660e */\n"
			"QTabWidget {\n"
			"    border: none;\n"
			"    background-color: transparent;\n"
			"}\n"
			"\n"
			"/* \u9690\u85cfQTabWidget\u7684\u5206\u5272\u7ebf */\n"
			"QTabWidget::pane {\n"
			"    border: none;\n"
			"}\n"
			"\n"
			"/* \u9690\u85cfQTabWidget\u6807\u7b7e\u680f\u7684\u8fb9\u6846 */\n"
			"QTabBar {\n"
			"    border: none;\n"
			"    background-color: transparent;\n"
			"}\n"
			"\n"
			"/* \u9690\u85cfQTabWidget\u6807\u7b7e\u4e4b\u95f4\u7684\u5206\u5272\u7ebf */\n"
			"QTabBar::tab {\n"
			"    border: none;\n"
			"}\n"
			"\n"
			"/* \u9690\u85cfQTabWidget\u6807\u7b7e\u7684\u7126\u70b9\u6846 */\n"
			"QTabBar::tab:focus {\n"
			"    border: none;\n"
			"}\n"
			"QTabWidget::tab-bar {\n"
			"    qproperty-drawBase: 0;\n"
			"    left: 0;\n"
			"    width: 0;\n"
			"    height: 0;\n"
			"}")
		self.tabWidget_main.setTabPosition(QTabWidget.North)
		self.tabWidget_main.setTabShape(QTabWidget.Triangular)
		self.tabWidget_main.setElideMode(Qt.ElideNone)
		self.tabWidget_main.setUsesScrollButtons(False)
		self.tabWidget_main.setDocumentMode(False)
		self.tabWidget_main.setTabsClosable(False)
		self.tabWidget_main.setMovable(False)
		self.tabWidget_main.setTabBarAutoHide(False)
		self.tab_player = QWidget()
		self.tab_player.setObjectName(u"tab_player")
		self.label_music_img_payer = QLabel(self.tab_player)
		self.label_music_img_payer.setObjectName(u"label_music_img_payer")
		self.label_music_img_payer.setGeometry(QRect(0, 5, 100, 100))
		self.label_music_img_payer.setStyleSheet(u"    QLabel {\n"
		                                         "        border-radius: 5px;      /* \u5706\u89d2\u534a\u5f84 */\n"
		                                         "    }")
		self.label_music_name_player = QLabel(self.tab_player)
		self.label_music_name_player.setObjectName(u"label_music_name_player")
		self.label_music_name_player.setGeometry(QRect(110, 5, 301, 31))
		self.label_music_name_player.setFont(font)
		self.label_music_name_player.setWordWrap(True)
		self.label_singer_player = QLabel(self.tab_player)
		self.label_singer_player.setObjectName(u"label_singer_player")
		self.label_singer_player.setGeometry(QRect(110, 35, 301, 16))
		font1 = QFont()
		font1.setFamily(u"\u5fae\u8f6f\u96c5\u9ed1")
		font1.setPointSize(8)
		self.label_singer_player.setFont(font1)
		self.label_singer_player.setStyleSheet(u"font-size: 8pt; color: #9f9f9f;")
		self.label_singer_player.setWordWrap(True)
		self.label_singer_player_2 = QLabel(self.tab_player)
		self.label_singer_player_2.setObjectName(u"label_singer_player_2")
		self.label_singer_player_2.setGeometry(QRect(110, 55, 300, 51))
		self.label_singer_player_2.setFont(font1)
		self.label_singer_player_2.setStyleSheet(u"QLabel {\n"
		                                         "    text-align: left;\n"
		                                         "	font-size: 8pt;\n"
		                                         "	color: #9f9f9f;\n"
		                                         "}")
		self.label_singer_player_2.setTextFormat(Qt.AutoText)
		self.label_singer_player_2.setWordWrap(True)
		self.listView_lyric = QListView(self.tab_player)
		self.listView_lyric.setObjectName(u"listView_lyric")
		self.listView_lyric.setGeometry(QRect(0, 115, 410, 251))
		self.listView_lyric.setFont(font)
		self.listView_lyric.setStyleSheet(u"QListView {\n"
		                                  "    background: transparent; /* \u900f\u660e\u80cc\u666f */\n"
		                                  "    border: 1px solid rgb(200, 200, 200); /* 1px\u8fb9\u7ebf\uff0c\u989c\u8272ARGB-3618616 */\n"
		                                  "    border-radius: 5px; /* 5px\u5706\u89d2 */\n"
		                                  "}\n"
		                                  "\n"
		                                  "QListView::item {\n"
		                                  "    background: transparent; /* \u975e\u9009\u4e2d\u900f\u660e */\n"
		                                  "    border-radius: 5px; /* 5px\u5706\u89d2 */\n"
		                                  "}\n"
		                                  "\n"
		                                  "QListView::item:hover {\n"
		                                  "    background: rgb(200, 195, 255); /* \u9f20\u6807\u5728\u9009\u9879\u4e0a\u65f6\u7684\u80cc\u666f\u989c\u8272\uff0cARGB-3619841 */\n"
		                                  "}\n"
		                                  "\n"
		                                  "QListView::item:selected {\n"
		                                  "    background: rgb(153, 153, 222); /* \u88ab\u9009\u4e2d\u65f6\u7684\u80cc\u666f\u989c\u8272\uff0cARGB-6710818 */\n"
		                                  "    color: black; /* \u8bbe\u7f6e\u9009\u4e2d\u65f6\u7684\u5b57\u4f53\u989c\u8272\u4e3a\u7eaf\u9ed1 */\n"
		                                  "}\n"
		                                  "")
		self.listView_lyric.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.horizontalSlider_music_place = QSlider(self.tab_player)
		self.horizontalSlider_music_place.setObjectName(u"horizontalSlider_music_place")
		self.horizontalSlider_music_place.setGeometry(QRect(0, 370, 411, 16))
		self.horizontalSlider_music_place.setStyleSheet(
			u"/* \u8bbe\u7f6eQSlider\u7684\u80cc\u666f\u4e3a\u900f\u660e */\n"
			"QSlider {\n"
			"    background: transparent;\n"
			"}\n"
			"\n"
			"/* \u5b9a\u4e49\u8fdb\u5ea6\u6761\u6837\u5f0f */\n"
			"QSlider::groove:horizontal {\n"
			"    background: transparent; /* \u672a\u5230\u8fbe\u533a\u57df\u900f\u660e */\n"
			"    border: 1px solid transparent;\n"
			"    height: 4px; /* \u8bbe\u7f6e\u8fdb\u5ea6\u6761\u9ad8\u5ea6 */\n"
			"    border-radius: 2px; /* \u8bbe\u7f6e\u8fdb\u5ea6\u6761\u5706\u89d2 */\n"
			"}\n"
			"\n"
			"/* \u5b9a\u4e49\u8fdb\u5ea6\u6761\u586b\u5145\u6837\u5f0f */\n"
			"QSlider::sub-page:horizontal {\n"
			"    background: rgb(200, 195, 255); /* \u8bbe\u7f6e\u8fdb\u5ea6\u6761\u989c\u8272 */\n"
			"    height: 4px; /* \u8bbe\u7f6e\u8fdb\u5ea6\u6761\u9ad8\u5ea6 */\n"
			"    border-radius: 2px; /* \u8bbe\u7f6e\u8fdb\u5ea6\u6761\u5706\u89d2 */\n"
			"}\n"
			"\n"
			"/* \u5b9a\u4e49\u6ed1\u5757\u6837\u5f0f */\n"
			"QSlider::handle:horizontal {\n"
			"    background: rgb(200, 195, 255); /* \u8bbe\u7f6e\u6ed1\u5757\u989c\u8272 */\n"
			"    width: 8px; /* \u8bbe\u7f6e"
			"\u6ed1\u5757\u5bbd\u5ea6 */\n"
			"    height: 3px; /* \u8bbe\u7f6e\u6ed1\u5757\u9ad8\u5ea6 */\n"
			"    margin: -5px 0; /* \u8c03\u6574\u6ed1\u5757\u4f4d\u7f6e\u4f7f\u5176\u5782\u76f4\u5c45\u4e2d */\n"
			"    border-radius: 2px; /* \u8bbe\u7f6e\u6ed1\u5757\u4e3a\u5706\u70b9 */\n"
			"}\n"
			"")
		self.horizontalSlider_music_place.setMaximum(1000)
		self.horizontalSlider_music_place.setPageStep(1)
		self.horizontalSlider_music_place.setValue(0)
		self.horizontalSlider_music_place.setOrientation(Qt.Horizontal)
		self.label_music_time_now = QLabel(self.tab_player)
		self.label_music_time_now.setObjectName(u"label_music_time_now")
		self.label_music_time_now.setGeometry(QRect(0, 385, 31, 16))
		self.label_music_time_now.setFont(font1)
		self.label_music_time_now.setStyleSheet(u"font-size: 8pt; color: #9f9f9f;")
		self.label_music_time_now.setWordWrap(True)
		self.label_music_time_all = QLabel(self.tab_player)
		self.label_music_time_all.setObjectName(u"label_music_time_all")
		self.label_music_time_all.setGeometry(QRect(380, 385, 31, 16))
		self.label_music_time_all.setFont(font1)
		self.label_music_time_all.setStyleSheet(u"font-size: 8pt; color: #9f9f9f;")
		self.label_music_time_all.setWordWrap(True)
		self.label_volume = QLabel(self.tab_player)
		self.label_volume.setObjectName(u"label_volume")
		self.label_volume.setGeometry(QRect(0, 405, 91, 16))
		self.label_volume.setFont(font1)
		self.label_volume.setStyleSheet(u"    font-size: 8pt;\n"
		                                "    color: rgb(105, 105, 105);")
		self.label_volume.setWordWrap(True)
		self.horizontalSlider_volume = QSlider(self.tab_player)
		self.horizontalSlider_volume.setObjectName(u"horizontalSlider_volume")
		self.horizontalSlider_volume.setGeometry(QRect(0, 420, 411, 16))
		self.horizontalSlider_volume.setStyleSheet(u"/* \u8bbe\u7f6eQSlider\u7684\u80cc\u666f\u4e3a\u900f\u660e */\n"
		                                           "QSlider {\n"
		                                           "    background: transparent;\n"
		                                           "}\n"
		                                           "\n"
		                                           "/* \u5b9a\u4e49\u8fdb\u5ea6\u6761\u6837\u5f0f */\n"
		                                           "QSlider::groove:horizontal {\n"
		                                           "    background: transparent; /* \u672a\u5230\u8fbe\u533a\u57df\u900f\u660e */\n"
		                                           "    border: 1px solid transparent;\n"
		                                           "    height: 4px; /* \u8bbe\u7f6e\u8fdb\u5ea6\u6761\u9ad8\u5ea6 */\n"
		                                           "    border-radius: 2px; /* \u8bbe\u7f6e\u8fdb\u5ea6\u6761\u5706\u89d2 */\n"
		                                           "}\n"
		                                           "\n"
		                                           "/* \u5b9a\u4e49\u8fdb\u5ea6\u6761\u586b\u5145\u6837\u5f0f */\n"
		                                           "QSlider::sub-page:horizontal {\n"
		                                           "    background: rgb(200, 195, 255); /* \u8bbe\u7f6e\u8fdb\u5ea6\u6761\u989c\u8272 */\n"
		                                           "    height: 4px; /* \u8bbe\u7f6e\u8fdb\u5ea6\u6761\u9ad8\u5ea6 */\n"
		                                           "    border-radius: 2px; /* \u8bbe\u7f6e\u8fdb\u5ea6\u6761\u5706\u89d2 */\n"
		                                           "}\n"
		                                           "\n"
		                                           "/* \u5b9a\u4e49\u6ed1\u5757\u6837\u5f0f */\n"
		                                           "QSlider::handle:horizontal {\n"
		                                           "    background: rgb(200, 195, 255); /* \u8bbe\u7f6e\u6ed1\u5757\u989c\u8272 */\n"
		                                           "    width: 8px; /* \u8bbe\u7f6e"
		                                           "\u6ed1\u5757\u5bbd\u5ea6 */\n"
		                                           "    height: 3px; /* \u8bbe\u7f6e\u6ed1\u5757\u9ad8\u5ea6 */\n"
		                                           "    margin: -5px 0; /* \u8c03\u6574\u6ed1\u5757\u4f4d\u7f6e\u4f7f\u5176\u5782\u76f4\u5c45\u4e2d */\n"
		                                           "    border-radius: 2px; /* \u8bbe\u7f6e\u6ed1\u5757\u4e3a\u5706\u70b9 */\n"
		                                           "}\n"
		                                           "")
		self.horizontalSlider_volume.setMaximum(100)
		self.horizontalSlider_volume.setPageStep(1)
		self.horizontalSlider_volume.setValue(50)
		self.horizontalSlider_volume.setOrientation(Qt.Horizontal)
		self.label_play_main = QLabel(self.tab_player)
		self.label_play_main.setObjectName(u"label_play_main")
		self.label_play_main.setGeometry(QRect(180, 440, 40, 40))
		self.label_last = QLabel(self.tab_player)
		self.label_last.setObjectName(u"label_last")
		self.label_last.setGeometry(QRect(140, 445, 30, 30))
		self.label_next = QLabel(self.tab_player)
		self.label_next.setObjectName(u"label_next")
		self.label_next.setGeometry(QRect(230, 445, 30, 30))
		self.tabWidget_main.addTab(self.tab_player, "")
		self.tab_search = QWidget()
		self.tab_search.setObjectName(u"tab_search")
		self.label_title_search = QLabel(self.tab_search)
		self.label_title_search.setObjectName(u"label_title_search")
		self.label_title_search.setGeometry(QRect(0, 0, 71, 21))
		self.label_title_search.setFont(font)
		self.listView_search = QListView(self.tab_search)
		self.listView_search.setObjectName(u"listView_search")
		self.listView_search.setGeometry(QRect(0, 60, 410, 340))
		self.listView_search.setFont(font)
		self.listView_search.setStyleSheet(u"QListView {\n"
		                                   "    background: transparent; /* \u900f\u660e\u80cc\u666f */\n"
		                                   "    border: 1px solid rgb(200, 200, 200); /* 1px\u8fb9\u7ebf\uff0c\u989c\u8272ARGB-3618616 */\n"
		                                   "    border-radius: 5px; /* 5px\u5706\u89d2 */\n"
		                                   "}\n"
		                                   "\n"
		                                   "QListView::item {\n"
		                                   "    background: transparent; /* \u975e\u9009\u4e2d\u900f\u660e */\n"
		                                   "    border-radius: 5px; /* 5px\u5706\u89d2 */\n"
		                                   "}\n"
		                                   "\n"
		                                   "QListView::item:hover {\n"
		                                   "    background: rgb(200, 195, 255); /* \u9f20\u6807\u5728\u9009\u9879\u4e0a\u65f6\u7684\u80cc\u666f\u989c\u8272\uff0cARGB-3619841 */\n"
		                                   "}\n"
		                                   "\n"
		                                   "QListView::item:selected {\n"
		                                   "    background: rgb(153, 153, 222); /* \u88ab\u9009\u4e2d\u65f6\u7684\u80cc\u666f\u989c\u8272\uff0cARGB-6710818 */\n"
		                                   "    color: black; /* \u8bbe\u7f6e\u9009\u4e2d\u65f6\u7684\u5b57\u4f53\u989c\u8272\u4e3a\u7eaf\u9ed1 */\n"
		                                   "}\n"
		                                   "")
		self.listView_search.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.lineEdit_search = QLineEdit(self.tab_search)
		self.lineEdit_search.setObjectName(u"lineEdit_search")
		self.lineEdit_search.setGeometry(QRect(0, 25, 411, 31))
		font2 = QFont()
		font2.setFamily(u"\u5fae\u8f6f\u96c5\u9ed1")
		font2.setPointSize(12)
		self.lineEdit_search.setFont(font2)
		self.lineEdit_search.setStyleSheet(u"QLineEdit {\n"
		                                   "    background: transparent;\n"
		                                   "    border: 1px solid rgb(200, 200, 200);\n"
		                                   "    border-radius: 5px;\n"
		                                   "    padding: 5px;\n"
		                                   "	padding-left: 25px;\n"
		                                   "}\n"
		                                   "")
		self.label_search_music = QLabel(self.tab_search)
		self.label_search_music.setObjectName(u"label_search_music")
		self.label_search_music.setGeometry(QRect(5, 30, 20, 20))
		self.tabWidget_main.addTab(self.tab_search, "")
		self.tab_player_list = QWidget()
		self.tab_player_list.setObjectName(u"tab_player_list")
		self.lineEdit_player_list = QLineEdit(self.tab_player_list)
		self.lineEdit_player_list.setObjectName(u"lineEdit_player_list")
		self.lineEdit_player_list.setGeometry(QRect(0, 25, 411, 31))
		self.lineEdit_player_list.setFont(font2)
		self.lineEdit_player_list.setStyleSheet(u"QLineEdit {\n"
		                                        "    background: transparent;\n"
		                                        "    border: 1px solid rgb(200, 200, 200);\n"
		                                        "    border-radius: 5px;\n"
		                                        "    padding: 5px;\n"
		                                        "	padding-left: 25px;\n"
		                                        "}\n"
		                                        "")
		self.label_search_player_list = QLabel(self.tab_player_list)
		self.label_search_player_list.setObjectName(u"label_search_player_list")
		self.label_search_player_list.setGeometry(QRect(5, 30, 20, 20))
		self.label_title_player_list = QLabel(self.tab_player_list)
		self.label_title_player_list.setObjectName(u"label_title_player_list")
		self.label_title_player_list.setGeometry(QRect(0, 0, 71, 21))
		self.label_title_player_list.setFont(font)
		self.listView_player_list = QListView(self.tab_player_list)
		self.listView_player_list.setObjectName(u"listView_player_list")
		self.listView_player_list.setGeometry(QRect(0, 60, 410, 340))
		self.listView_player_list.setFont(font)
		self.listView_player_list.setStyleSheet(u"QListView {\n"
		                                        "    background: transparent; /* \u900f\u660e\u80cc\u666f */\n"
		                                        "    border: 1px solid rgb(200, 200, 200); /* 1px\u8fb9\u7ebf\uff0c\u989c\u8272ARGB-3618616 */\n"
		                                        "    border-radius: 5px; /* 5px\u5706\u89d2 */\n"
		                                        "}\n"
		                                        "\n"
		                                        "QListView::item {\n"
		                                        "    background: transparent; /* \u975e\u9009\u4e2d\u900f\u660e */\n"
		                                        "    border-radius: 5px; /* 5px\u5706\u89d2 */\n"
		                                        "}\n"
		                                        "\n"
		                                        "QListView::item:hover {\n"
		                                        "    background: rgb(200, 195, 255); /* \u9f20\u6807\u5728\u9009\u9879\u4e0a\u65f6\u7684\u80cc\u666f\u989c\u8272\uff0cARGB-3619841 */\n"
		                                        "}\n"
		                                        "\n"
		                                        "QListView::item:selected {\n"
		                                        "    background: rgb(153, 153, 222); /* \u88ab\u9009\u4e2d\u65f6\u7684\u80cc\u666f\u989c\u8272\uff0cARGB-6710818 */\n"
		                                        "    color: black; /* \u8bbe\u7f6e\u9009\u4e2d\u65f6\u7684\u5b57\u4f53\u989c\u8272\u4e3a\u7eaf\u9ed1 */\n"
		                                        "}\n"
		                                        "")
		self.listView_player_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.tabWidget_main.addTab(self.tab_player_list, "")
		self.tab_album_list = QWidget()
		self.tab_album_list.setObjectName(u"tab_album_list")
		self.label_album_img = QLabel(self.tab_album_list)
		self.label_album_img.setObjectName(u"label_album_img")
		self.label_album_img.setGeometry(QRect(0, 0, 100, 100))
		self.label_album_img.setStyleSheet(u"    QLabel {\n"
		                                   "        border-radius: 5px;      /* \u5706\u89d2\u534a\u5f84 */\n"
		                                   "    }")
		self.tabWidget_main.addTab(self.tab_album_list, "")
		self.tab_setting = QWidget()
		self.tab_setting.setObjectName(u"tab_setting")
		self.label_title_player_list_2 = QLabel(self.tab_setting)
		self.label_title_player_list_2.setObjectName(u"label_title_player_list_2")
		self.label_title_player_list_2.setGeometry(QRect(0, 0, 71, 21))
		self.label_title_player_list_2.setFont(font)
		self.label_bass_version = QLabel(self.tab_setting)
		self.label_bass_version.setObjectName(u"label_bass_version")
		self.label_bass_version.setGeometry(QRect(0, 385, 301, 16))
		self.label_bass_version.setFont(font1)
		self.label_bass_version.setStyleSheet(u"font-size: 8pt; color: #9f9f9f;")
		self.label_bass_version.setWordWrap(True)
		self.pushButton_QQLogin = QPushButton(self.tab_setting)
		self.pushButton_QQLogin.setObjectName(u"pushButton_QQLogin")
		self.pushButton_QQLogin.setGeometry(QRect(0, 30, 151, 41))
		font3 = QFont()
		font3.setFamily(u"\u5fae\u8f6f\u96c5\u9ed1")
		font3.setPointSize(11)
		self.pushButton_QQLogin.setFont(font3)
		self.pushButton_QQLogin.setStyleSheet(u"QPushButton {\n"
		                                      "    background-color: #3498db;  /* \u84dd\u8272 */\n"
		                                      "    color: #ffffff;  /* \u767d\u8272 */\n"
		                                      "    border: 1px solid #3498db;  /* \u84dd\u8272\u8fb9\u6846 */\n"
		                                      "    border-radius: 5px;  /* \u5706\u89d2 */\n"
		                                      "    padding: 5px 10px;  /* \u6309\u94ae\u5185\u8fb9\u8ddd */\n"
		                                      "}\n"
		                                      "\n"
		                                      "QPushButton:hover {\n"
		                                      "    background-color: #2980b9;  /* \u9f20\u6807\u60ac\u505c\u65f6\u7684\u84dd\u8272 */\n"
		                                      "    border: 1px solid #2980b9;  /* \u9f20\u6807\u60ac\u505c\u65f6\u7684\u8fb9\u6846 */\n"
		                                      "}\n"
		                                      "\n"
		                                      "QPushButton:pressed {\n"
		                                      "    background-color: #21618c;  /* \u6309\u94ae\u6309\u4e0b\u65f6\u7684\u84dd\u8272 */\n"
		                                      "    border: 1px solid #21618c;  /* \u6309\u94ae\u6309\u4e0b\u65f6\u7684\u8fb9\u6846 */\n"
		                                      "}\n"
		                                      "")
		icon = QIcon()
		icon.addFile(u"C:/Users/zhaoh/Downloads/2023\u5e7410\u670818\u65e519\u65f613\u520619\u79d2.jpg", QSize(),
		             QIcon.Normal, QIcon.Off)
		self.pushButton_QQLogin.setIcon(icon)
		self.pushButton_QQLogin.setIconSize(QSize(30, 30))
		self.pushButton_QQLogin.setCheckable(False)
		self.pushButton_QQLogin.setChecked(False)
		self.pushButton_QQLogin.setAutoRepeat(False)
		self.pushButton_QQLogin.setAutoExclusive(False)
		self.pushButton_QQLogin.setAutoDefault(False)
		self.pushButton_QQLogin.setFlat(True)
		self.label_about_title = QLabel(self.tab_setting)
		self.label_about_title.setObjectName(u"label_about_title")
		self.label_about_title.setGeometry(QRect(0, 90, 171, 21))
		self.label_about_title.setFont(font)
		self.label_about_md = QLabel(self.tab_setting)
		self.label_about_md.setObjectName(u"label_about_md")
		self.label_about_md.setGeometry(QRect(0, 110, 401, 161))
		self.label_about_md.setTextFormat(Qt.MarkdownText)
		self.checkBox_translate = QCheckBox(self.tab_setting)
		self.checkBox_translate.setObjectName(u"checkBox_translate")
		self.checkBox_translate.setGeometry(QRect(170, 30, 151, 21))
		self.checkBox_translate.setStyleSheet(u"QCheckBox {\n"
		                                      "    color: #333333; /* \u6587\u5b57\u989c\u8272 */\n"
		                                      "}\n"
		                                      "\n"
		                                      "QCheckBox::indicator {\n"
		                                      "    width: 16px;\n"
		                                      "    height: 16px;\n"
		                                      "}\n"
		                                      "\n"
		                                      "QCheckBox::indicator:unchecked {\n"
		                                      "    border: 1px solid #3498db; /* \u84dd\u8272\u8fb9\u6846 */\n"
		                                      "    background-color: transparent;\n"
		                                      "    border-radius: 5px\n"
		                                      "}\n"
		                                      "\n"
		                                      "QCheckBox::indicator:checked {\n"
		                                      "    border: 1px solid #3498db; /* \u84dd\u8272\u8fb9\u6846 */\n"
		                                      "    background-color: #3498db; /* \u84dd\u8272\u80cc\u666f */\n"
		                                      "    border-radius: 5px\n"
		                                      "}")
		self.checkBox_auto_play = QCheckBox(self.tab_setting)
		self.checkBox_auto_play.setObjectName(u"checkBox_auto_play")
		self.checkBox_auto_play.setGeometry(QRect(170, 50, 161, 21))
		self.checkBox_auto_play.setStyleSheet(u"QCheckBox {\n"
		                                      "    color: #333333; /* \u6587\u5b57\u989c\u8272 */\n"
		                                      "}\n"
		                                      "\n"
		                                      "QCheckBox::indicator {\n"
		                                      "    width: 16px;\n"
		                                      "    height: 16px;\n"
		                                      "}\n"
		                                      "\n"
		                                      "QCheckBox::indicator:unchecked {\n"
		                                      "    border: 1px solid #3498db; /* \u84dd\u8272\u8fb9\u6846 */\n"
		                                      "    background-color: transparent;\n"
		                                      "    border-radius: 5px\n"
		                                      "}\n"
		                                      "\n"
		                                      "QCheckBox::indicator:checked {\n"
		                                      "    border: 1px solid #3498db; /* \u84dd\u8272\u8fb9\u6846 */\n"
		                                      "    background-color: #3498db; /* \u84dd\u8272\u80cc\u666f */\n"
		                                      "    border-radius: 5px\n"
		                                      "}")
		self.tabWidget_main.addTab(self.tab_setting, "")
		self.label_partition_2 = QLabel(Form_Main)
		self.label_partition_2.setObjectName(u"label_partition_2")
		self.label_partition_2.setGeometry(QRect(10, 535, 411, 2))
		self.label_partition_2.setStyleSheet(u"background-color: #000;")
		self.label_search = QLabel(Form_Main)
		self.label_search.setObjectName(u"label_search")
		self.label_search.setGeometry(QRect(135, 555, 30, 30))
		self.label_player_list = QLabel(Form_Main)
		self.label_player_list.setObjectName(u"label_player_list")
		self.label_player_list.setGeometry(QRect(260, 555, 30, 30))
		self.label_player = QLabel(Form_Main)
		self.label_player.setObjectName(u"label_player")
		self.label_player.setGeometry(QRect(10, 555, 30, 30))
		self.label_setting = QLabel(Form_Main)
		self.label_setting.setObjectName(u"label_setting")
		self.label_setting.setGeometry(QRect(385, 555, 30, 30))
		self.groupBox_quick_box = QGroupBox(Form_Main)
		self.groupBox_quick_box.setObjectName(u"groupBox_quick_box")
		self.groupBox_quick_box.setGeometry(QRect(10, 450, 411, 81))
		self.groupBox_quick_box.setStyleSheet(u"border: none;\n"
		                                      "background-color: transparent;")
		self.label_music_img_box = QLabel(self.groupBox_quick_box)
		self.label_music_img_box.setObjectName(u"label_music_img_box")
		self.label_music_img_box.setGeometry(QRect(0, 5, 70, 70))
		self.label_music_img_box.setStyleSheet(u"    QLabel {\n"
		                                       "        border-radius: 5px;      /* \u5706\u89d2\u534a\u5f84 */\n"
		                                       "    }")
		self.label_music_name_box = QLabel(self.groupBox_quick_box)
		self.label_music_name_box.setObjectName(u"label_music_name_box")
		self.label_music_name_box.setGeometry(QRect(72, 25, 261, 30))
		self.label_music_name_box.setFont(font)
		self.label_music_name_box.setWordWrap(True)
		self.label_next_box = QLabel(self.groupBox_quick_box)
		self.label_next_box.setObjectName(u"label_next_box")
		self.label_next_box.setGeometry(QRect(370, 28, 25, 25))
		self.label_play_main_2 = QLabel(self.groupBox_quick_box)
		self.label_play_main_2.setObjectName(u"label_play_main_2")
		self.label_play_main_2.setGeometry(QRect(330, 25, 30, 30))

		self.retranslateUi(Form_Main)

		self.tabWidget_main.setCurrentIndex(0)
		self.pushButton_QQLogin.setDefault(False)

		QMetaObject.connectSlotsByName(Form_Main)

	# setupUi

	def retranslateUi(self, Form_Main):
		Form_Main.setWindowTitle(QCoreApplication.translate("Form_Main", u"MCQTSS Music", None))
		self.label_title.setText(
			QCoreApplication.translate("Form_Main", u"<html><head/><body><p><span style=\" font-size:16pt;\n"
			                                        "                    font-weight:600;\">MCQTSS Music</span></p></body></html>\n"
			                                        "                ", None))
		self.label_ver.setText(
			QCoreApplication.translate("Form_Main", u"<html><head/><body><p><span style=\" font-size:8pt;\n"
			                                        "                    color:#9f9f9f;\">1.0.7(Python Version)</span></p></body></html>\n"
			                                        "                ", None))
		self.label_close.setText(
			QCoreApplication.translate("Form_Main", u"<html><head/><body><p><img width=\"20\" height=\"20\"\n"
			                                        "                    src=\"data:application/octet-stream;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAYAAACtWK6eAAAAAXNSR0IArs4c6QAAD0tJREFUeF7tnXmOJMUVh9+rQVyA5QIYJLgAyLK4gQ22ZLozknVm6Mqafd83thn2namsAe/OyGlbssG+AbIsuACWwFyA5QIjpp5VdI/pYaa7MyNeVFVk/PgPKd/LiO/lF1VTv+4uJvwHAiCwLgEGGxAAgfUJQBA8HSCwAQEIgscDBCAIngEQcCOAVxA3bqhKhAAESWTQ2KYbAQjixg1ViRCAIIkMGtt0IwBB3LihKhECECSRQWObbgQgiBs3VCVCAIIkMmhs040ABHHjhqpECECQRAaNbboRgCBu3FCVCAEIksigsU03AhDEjRuqEiEAQRIZNLbpRgCCuHFDVSIEIEgig8Y23QhAEDduqEqEAARJZNDYphsBCOLGDVWJEIAgiQwa23QjAEHcuKEqEQIQJJFBY5tuBCCIGzdUJUIAgiQyaGzTjQAEceOGqkQIQJBEBo1tuhGAIG7cUJUIAQiSyKCxTTcCEMSNG6oSIQBBEhk0tulGAIK4cUNVIgQgSCKDxjbdCEAQN26oSoQABElk0NimGwEI4sYNVYkQgCCJDBrbdCMAQdy4oSoRAhAkkUFjm24EOiGIMf27J9u3dvSFGwZUaRLo0jyiFWRxcen+Xm/LSRF5gJnumAxYhL5mpn+Px+MLly9f+lRz6Oi1MYGVefSOi9BPr58HfzIeX30h1nlEKYgxxVkiOrf+yOQKEZ+3tnwGD3Z4AivzkBNEfOsGdzsX4zyiE2RhYemuLVt6/2049iiH0nBvc3HZ5ofVD8u8enX8k+XlS1/OxcIbLiI6QbKs+Bsz/bLh/khEztb16Nmm1+O65gSyrH+GmRu/SovQ3+u6/FXz"
			                                        "O8z+yugEMab4hohua4nujLXlcy1rcPkGBIwpThNR24PnW2vL22MCG5UgCwvb792y5ZbP3ADLaWtHz7vVomotAWP6p4jY6cC5evW7+5aXP/hPLESjEmTl40P+3BWuCJ2q6/IF13rUEWVZcZKZPA4auSemj+OjEmTygGZZ8dW1jxHdHlg+ae3wvFtt2lXGDE4QifMBM/kYvq7LO2OiGJ0gxhQfEtFDPpCZ5URVjS749EitNs/7x0XY92D5yNry4ZjYRSfISiDFH2/ymfumMxCh43Vdvrjphbhg8qp9jJk8DxS5Mh7Lg7EFhtEJMnle23z2vvHzzcesHb4EB9YnYMzgKJFoHCRRZlJRCqIpCTMdraryZUhyI4E8L46IkMYBEqUcEyLRCrLyD/Z2QdV6EojwkboevgJJfiCQZYPDzOJ9cMQe1EYtyOoriUtgdRMX5LC1o1chyeQtbP8QEWscGNEHtNELsiKJe3C1VghmOlRV5WspS5LnxUERUjgouhHMdkKQ1XzEM8Ba0UKED9b18PUUJcmywQFm8T4guhTIdkaQlVcSvyDrmhQicrCuR0lJkmX9A8zsLQdRt4LYTgkyecCVAq1JqwPWlm+k8EpiTLGfiLwPhC4GsJ0TZPXtlkKw9f3brf11PXyzy5Jk2WAfs3gfBF0NXjspyOrbLaWAS/ZZO3qri5IY099LxAoHQHcD184KsvJ2Sy3o2mtt+XaXJDGm2ENE3uJ3PWjttCArb7fUAq89dT16pwuSZFl/NzN7C59CwNp5QVZzEq3ga7e15bsxS2JMsYuIFERPI1hNQpDVt1sqARgz76qq4XsxSpLng50i4i14SoFqMoKsvt1SCsJkZ12PLsYkSZb1dzCzt9ipBalJCbIiiVYgRjusLYcxSGJMMSAib6FTDFCTE2T1Bxy1grFBVY3KeZYkz/uFCGuInExwet3P583zcEOuTTEgK+q6HIVcq2vvLCv6zOQtcAqB6XqMk3wFuQZDMSjrWzu85Pogh6gzZrBEJAridjcobcI9a"
			                                        "UFW325pBWZLVVW+3wR66GvyvHhahDSE7VxA2pZ98oKs/sNdKzh7uq6HH7Qdgub1WTbYzizeoopIZ4JRH74QZJWeVoAmwjOTREsOIoo+EPWRAv9IX4eeVpBGJNutHf1Ga0hN+hjT30bE3q9eMQehTTi1vQavID8iphWojce07fLl8rdtB+Jy/eJisbXXI28hReILQF14tamBIDehpRisba3r0e/aDKTttVnWf4qZNUSMJvhsy8jnegiy7tsttYDtKWvL3/sMab1aY4onichbQGaZ+8AzBL8mPSHIBpQUg7Yn63r4hyYDaXpNlg2eYBZv8URoboPOpixCXgdBNqGrGLg9Ye3ojxrDNKb/OBErCMdzF3Bq8NHsAUEa0FQM3h63tvxTg1uue4kxxWNE5C0aM81NsOnDI3QtBGlIWCtjEJHH6nr054a3ve6yLOs/ysxegk0azjKrcdn3LGsgSAv6WpIQ0aPWllWLW0/+on1ORE5irb0P5GhDPfI/Xt1uqzpXKwZyeVUNbZNV5fnAiEgroW7ed/oBZpP9zfM1eAVxmI5iMGfqelRvtIQs62fM3EikjfpMM7h0QDq3JRDEcTSKAV1mbXn5Zsswplgkog0FarJ8EQkeWDZZR4zXQBCPqekFdb3Fqrq4vHYpeb5jQWR8U3FaLjlYUNlyHVFeDkE8x6YY2C3UdfmXyXKyrHiEma4TxmWZIqweULqsI+YaCKIwPcXg7pGV5cj3ovj9J2rBpN864q6GIErz0wrwlJbjHUgqrSP6NhBEcYRaQZ7PknyCSJ/7drUWgihPVivQc1xW6wDS8T7JlEGQAKPWC/aaL46ZGwePzbviSggS6BnQCviaLE9ENg0cm/TBNTcSgCABnwqtoG+TJa4bNAbcWjKtIUjgUSsGfjeslPnGgDHwdpJrD0GmMHKt4G/tUkXo/8HiFLaQ7C0gyJRGb8zg1zoB4GTB/Ii1w79OaelJ3waCTGn8EGRKoJVvA0GUgd6sHd5iTQFyoFtAkEBgr7XFP9IDAw7cHo"
			                                        "IEBIyPeQPCnVJrCBIINILCQGCn3BaCBACOHzUJAHVGLSGIMnj8sKIy0Bm3gyCKA8CPuyvCnJNWEERpEPiFKSWQc9YGgigMBL9yqwBxTltAEM/B4I82eAKc83II4jEg/NkfD3iRlEIQx0HhD8c5gousDII4DCzLBk8xi/fXnjX5TUCtwFGEt9b10PvbqBxwRV0CQVqOL8+LrSL+X5jZ5nfItYJHZtpWVdP5YtGWWOf2cgjSYjTG7NhGNPb+quVZfv0BUW+7tRe9vxG3BbaoL4UgDcen9d0gPn+3SiuIxHeENBz65FfTml+a7pX4CrZ0Zw9BNpk9vsQzXTkmO4cgG8wfXwOdthwQZIP553m/EOGhwiMS7Ps59IJKGVTVqFTYa+da4BXkJiM1phgQ0UXfaU/jm50UA8sd1pYaB4IvtrmqhyA/GkeW9Xcw83u+U5pmMKcYXO6s65H3weDLbp7qIciaaeT5YKeIvOs7oFkEcooB5q6qGnofEL4M56UegqxOwphiFxG94z+Y2QVxikHmbmtL74PCn+XsO0CQ778TsL+bmd/2Hcc8BHCKgeaeuh4pHBi+VGdbn7wgxhR7iOgt3zEw01JVle/79tGoVww291pbeh8cGnuaVY+kBTGmv5eI3/SHz31rh5f8++h1UAw491k78j5A9HY23U7JCpJlS/uYe2/44hahoq7LkW+fEPV6Qed4f11fUjhIQuwybM8kBcnzwT4R8ZaDef4DNq3Ak5n3V9UwOUmSE8SYYj8Rva5w7kQTrGkFn0R0wNrS+2BRYD+1FkkJkmWDA8zymi9dEYkuUFMMQA/W9VDjgPEdw1TqkxEkz4uDIvSqL1VmjjZIUwxCD1VV6X3Q+M5iGvVJCGJM/xARv6IANPoATS8QlcPWjrwPHIWZBG3ReUGybHCYWV72pSginQnOFIPRI3U91Dh4fMcTrL7TguR5cUSEXlKg17nATDEgPVpVpfcBpDCjIC06K4gx/aNE/KI/NelsUKYXlMoxa0caB5H/uJQ7dFKQLCu"
			                                        "OMdMFX1Yi3Q/IFAPT43VdKhxIvlPTre+cIHnePy7C530xpRSMKQanJ6pq5H0w+c5Os75TghgzOEEkLygASi4Q0wtQ+aS1Q+8DSmGGKi06I0iWFSeZ6XlfKiKcVBC2lpdekEqn6rrUOKh8x+ld3wlBjOmfIuLnfGkwUzIB2HqstAJVIjlt7cj7wPKdqW999IIYU5wmomd9QRClEXw14aQYrJ6xtvQ+uJqsOdQ1UQuSZf0zzPyMLxwR7nzg1ZaRYsB6tq5HCgdY2x3oXB+tIMYUZ4nonC8GZup00OXDRzFoPWdt6X2Q+ezFtTZKQbTkIOpuwOX6QPy4Ti9wpSgliU6QxcWl+3s9/piIb/V5CESok8GWD5P1anWCV7kyHsuDly9f+jTEGkP1jE4QY4oPieghHyDM0rlAy4dHk1qlAPYja8uHm9xvXq6JUZBviOg2d4DdCrLcObSvVAhiv7W2vL39nWdXEZUgCwvb792y5ZbPXHGJdCfAcmXgW+cbyF69+t19y8sf/Md3HdOqj0oQY/p3E/HnbnC6EVy57V23yi+YlXusHX2hu6Jw3aISZIIhy4qvmOmOlkiiD6xa7jf45S4BrQh9XdflncEXp3iD6AQxZvAPIvl5UwYiEnVQ1XSfs7iufVDL/7R2+ItZrNX1ntEJsvIxb++ThhuO8rP3hnubi8vaZFLj8fgBfMw7hbFtPhS5QsTnY01vp4BQ9RYr85ATm2RTUR5W0b2CXJvswsLSXb1e7xVmenDNx77fEtG/xuPxhdhOKtUndgbNVl/ZjxPRz9bOQ4Q+Ho/Hh5eXL305g2V53zJaQdbufPLx7+T/Y/r40Htyc9ygS/PohCBz/KxgaZETgCCRDxDLD0sAgoTli+6RE4AgkQ8Qyw9LAIKE5YvukROAIJEPEMsPSwCChOWL7pETgCCRDxDLD0sAgoTli+6RE4AgkQ8Qyw9LAIKE5YvukROAIJEPEMsPSwCChOWL7pETgCCRDxDLD0sAgoTli+6RE4AgkQ8Qyw9LAIKE5Yvu"
			                                        "kROAIJEPEMsPSwCChOWL7pETgCCRDxDLD0sAgoTli+6RE4AgkQ8Qyw9LAIKE5YvukROAIJEPEMsPSwCChOWL7pETgCCRDxDLD0sAgoTli+6RE4AgkQ8Qyw9LAIKE5YvukROAIJEPEMsPSwCChOWL7pETgCCRDxDLD0sAgoTli+6RE4AgkQ8Qyw9LAIKE5YvukROAIJEPEMsPSwCChOWL7pETgCCRDxDLD0sAgoTli+6RE4AgkQ8Qyw9LAIKE5YvukROAIJEPEMsPSwCChOWL7pET+B8awI8UZTs5HAAAAABJRU5ErkJggg==\"/></p></body></html>\n"
			                                        "                ", None))
		self.label_partition_1.setText("")
		self.label_music_img_payer.setText(
			QCoreApplication.translate("Form_Main", u"<html><head/><body><p><img width=\"100\" height=\"100\"\n"
			                                        "                    src=\"https://y.qq.com/music/photo_new/T002R300x300M000003jpkCG0OOSea_1.jpg?max_age=2592000\"/></p></body></html>",
			                           None))
		self.label_music_name_player.setText(QCoreApplication.translate("Form_Main",
		                                                                u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:600;\">\u30dd\u30b1\u30c3\u30c8\u3092\u3075\u304f\u3089\u307e\u305b\u3066</span></p></body></html>",
		                                                                None))
		self.label_singer_player.setText(QCoreApplication.translate("Form_Main", u"rionos", None))
		self.label_singer_player_2.setText(QCoreApplication.translate("Form_Main",
		                                                              u"<html><head/><body><p><span style=\" color:#9f9f9f;\">\u4e13\u8f91\u7b80\u4ecb:Key20\u5468\u5e74\u8a18\u5ff5\u7dcf\u9078\u6319\u3067\u30e6\u30fc\u30b6\u30fc\u6295\u7968\u306b\u3088\u308b\u3001Key\u6b4c\u66f2\u30d9\u30b9\u30c8\u30e9\u30f3\u30ad\u30f3\u30b0\u306eTOP10\u306e\u53ce\u9332\u306b\u52a0\u3048 \u30e9\u30f3\u30ad\u30f3\u30b020\u4f4d\u307e\u3067\u306e\u4e2d\u304b\u3089\u9078\u5225\u3057\u305f\u8a18\u5ff5\u30a2\u30ec\u30f3\u30b8\u3092\u52a0\u3048\u305f2\u679a\u7d44\u30d9\u30b9\u30c8\u76e4\uff01</span></p></body></html>",
		                                                              None))
		self.label_music_time_now.setText(QCoreApplication.translate("Form_Main", u"00:00", None))
		self.label_music_time_all.setText(QCoreApplication.translate("Form_Main", u"06:47", None))
		self.label_volume.setText(QCoreApplication.translate("Form_Main", u"\u97f3\u91cf:50%", None))
		self.label_play_main.setText("")
		self.label_last.setText(
			QCoreApplication.translate("Form_Main", u"<html><head/><body><p><img width=\"30\" height=\"30\"\n"
			                                        "                    src=\"data:application/octet-stream;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAYAAACtWK6eAAAAAXNSR0IArs4c6QAAETFJREFUeF7tnXuQHFd1h89p7WRFRcSQkAeOCVSs0ipzT6/sEklscDlSkSIQkvDUEkJhsLExOJCAgTwwYBtwnn5gGeNgDHaAJBSEpMjDD5mH8gAZKmLl7dtbllE5IMvGCXEiEJi1ZM9NXWksa7WP6b7nds/09q//1Tnn3vud+TRzd6b7MuECARBYkgCDDQiAwNIEIAheHSCwDAEIgpcHCEAQvAZAIIwA3kHCuCGrJQQgSEsajWWGEYAgYdyQ1RICEKQljcYywwhAkDBuyGoJAQjSkkZjmWEEIEgYN2S1hAAEaUmjscwwAhAkjBuyWkIAgrSk0VhmGAEIEsYNWS0hAEFa0mgsM4wABAnjhqyWEIAgLWk0lhlGAIKEcUNWSwhAkJY0GssMIwBBwrghqyUEIEhLGo1lhhGAIGHckNUSAhCkJY3GMsMIQJAwbshqCQEI0pJGY5lhBCBIGDdktYQABGlJo7HMMAIQJIwbslpCAIK0pNFYZhgBCBLGDVktIQBBWtJoLDOMAAQJ44aslhCAIC1pNJYZRgCChHFDVksIQJCWNLquZU5MTDxxbGzsN4noHcz8KBHNMPPX16xZc8mOHTt+UNc8Yo0DQWKRRB0yxpzHzBcR0dOPx+Gc+/zY2Nir77zzzvuahAqCNKlbIzxXEfkzInr7gCnOPPTQQ2fec8893xnhpcybGgRpSqdGdJ7dbvdnkiS5moheVGSKzPyCLMtuLhI7CjEQZBS60NA5pGn6y845L0e3xBIus9a+s0T8UEMhyFDxN3dwEXkDEXk5OiVXsd1au7lkztDCIcjQ0Dd34DRNr3TOvSVwBRAkEFypNBF5JjOf"
			                                        "5pzbzMx7nXNf63Q6t05PT3+7VCEEFyYgIif33zVeUDhpYSAEUcArlGqMuZGZX3N8MDPf3+v1Lsvz/IOFCiGoMAFjzPO8HMy8rnDS4oEQRAlw2XQReRURfWy5IGZ+ZpZlO6ucR5tqi8ib+u8cMT6SQ5CqXjwiMklEdw6q75y7Ps/z8wfF4d8HEzDGXMPMbxwcWTgCghRGVTIwTdM/cM79cYG0B6y1Ty0Qh5AlCPT3G9cS0a9EhgRBIgM9Wi5N0886536jSP0kSTbOzMx8rUgsYuYTEJFf63+k+tkK2ECQCqAeLikiXySiTQXrb7bWbi8Yi7A+gTRNL3TOXVEhEAhSFVwIUhXZI3VF5Doien21oxAEqQowBKmG7Pr165+xatWqG5j5OdWMMK8qBKkKMgSJT1ZEXtzfbzwtfvVFK0KQqkBDkLhkjTG/x8x/qqnKzN/o9XpTzPzVgnUgSEFQpcMgSGlkSyaIyIeJ6FxlxZuTJJmamZn5voi4grUgSEFQpcMgSGlkCxJExH+U+gQRnamsdrm19ugNUhBESTNGOgTRUUzTdEv//g3Vl6jMfHaWZTcdOxsIoutNlGwIEo5RRN5BRJeFVzic+U2/35idnV2w34AgSrIx0iFIGMU0TW9yzr06LPtIlnPuFuecl+N7i9WBIBq6kXIhSDmQExMTJ3Y6nU8T0bPKZS6IvsJa+7blakAQJeEY6RCkOEUReQkR/QUR/XjxrIWRzHxOlmU3DqoBQQYRquHfIUgxyCJyMRFdUix6yai9/f3GV4rUgSBFKFUcA0EGAxYR/yfcVw6OXDqCmW89ePDg1O7duw8UrQNBipKqMA6CLA1XRH6SiP6BiH5B0wLn3JV5nr+1bA0IUpZYBfEQZHGoaZq+0Dnnv5d4khL7a621Hw2pAUFCqEXOgSALgaZp+l7nnPZBbPf2fzJyR2jLIEgouYh5EGQ+TBH5JBG9XIn4trm5uak9e/Z8V1MHgmjoRcqFIEdArlu37imdTmcbM5+qQRu631hsTAii6USkX"
			                                        "Ahy+K4/f7/43xDRGiXWc621H1HWOJoOQWKRVNRpuyAi8j4i8udvaK59zDyVZdkOTZHjcyFITJqBtdosiIh8hoj8t+Oaa9vc3NwW7X4DH7E0Lagwt42CpGn6ZOfcvxBRqkHLzFdlWXahpsZyuXgHqYpsibptEyRN0+c75/6OiFaXwLQg1Dl3Xp7nN2hqDMqFIIMI1fDvbRLEGHMpM79bidWfBzhlrf2yss7AdAgyEFH1AW0RpMwTJJehvm18fHxq586dtZwHCEGqf/0PHGGlC7J27dofWb16tf82++cGwlgmgJnfn2VZ6AE3QUNDkCBscZNWsiAi8lwi8odbrtJQc869Ls9z/8SSWi8IUivuxQdbqYLEuH/DOXe/32/kef6lYbQKggyD+nFjrkRBROSfiehXlXhvHxsbm9q1a9d+ZZ3gdAgSjC5e4koSpNvtrkmSZJqI1ioJXW2tfbOyhjodgqgR6gusFEH654vfriXCzOdnWXa9tk6MfAgSg6KyxkoQxBjzTmZ+rxLFt5xzW4a131hs7hBE2dEY6U0XRET+iYg0Ryh7jJ/r/9jw/2IwjVUDgsQiqajTVEFOOumkJ5xwwgmzzPwMxfJ96lZr7e8qa1SSDkEqwVquaBMFMcZsZuYvlFvpwmhmfn2WZR/S1qkqH4JURbZE3aYJIiJ/SER/VGKJi4V+q/98qn9X1qk0HYJUirdY8SYJYoz5LDMXOpF3qdU75z7f//Lvf4sRGl4UBBke+6MjN0GQbrf7Q0mS3ENEP61Edo219neUNWpLhyC1oV56oFEXJE3TM/s3N2lpvcFa65+r25gLgoxAq0ZZkBjn/RHRA/3nU/3bCOAuNQUIUgpXNcGjKoiI+Lv+/GmxwZf/S9ehQ4em7rrrrgeDiwwxEYIMEf5jQ4+gIKtE5F4iUh1p5pz7QJ7nbxoBxMFTgCDB6OIljpIgxphnM3OMP702br+xWEchSLzXeXClURFERPzTzy8PXsiRxP/q/2TkX5V1RiIdgoxAG0ZBEGPMp5n5ZU"
			                                        "ocX/Tnb9x9993/o6wzMukQZARaMWxB+vuNkzQonHPX5nn+Rk2NUcyFICPQlWEKIiJ+v/FsJYYLrLXXKWuMZDoEGYG2DEsQEfHni/tzxkOv/+7vN/wTElfkBUFGoK1DFMT/KTf0o9X2TqczNT09/e0RQFjZFCBIZWiLFx6GIBs2bFj36KOP7i4+y3mRH7TW/nZgbqPSIMgItGsYgojIyUS0J3D5EGQhuO3W2s2BPGtP49pHVAw4DEH8dI0x/6m4GxAfseb3HIIoHFg2dViCiMhWItL8FASb9Mc7C0FWmiB+PSLy9QjPsMKfeYkgyEoUpC/JXiJ6mmZ9+KIQgmhePyP5EevYSUU6ehk/NansVRK3MDbpATxFxN8Ke3VA6rEp+LGiEmAd6RAkkHKaphudc/8RmH5s2orYl+B7kAivBG2JYf0Va5l5JyLiv0RUPYAaN0xpXxnV5eMdJAJbEflLIjpLUwq33GroVZcLQSKxTdP0fOec9kkkeGhDpH7EKgNBYpH0B5mnaeqcm4lQsnG34WIPEqHr2hIjuAdZsKRNmzaNPfjgg7ucc0a5Xjw4TgkwRjreQWJQXKRGmqbXO+fO05THo0c19OLkQpA4HBetkqbpa5xzNyqHeKD/8OqRfpgcPmIpuxwjvQkfsY5fpzGmy8y5dv04/kBLMCwf7yBh3Epl+QdaM/MdzHxqqcSFwThARwmwbDoEKUtMEW+MuYaZtU80wRFsih6UTYUgZYkp440xr2Dmv1aWGblDdbAHUXY0RnoT9yCLrbvb7ZokSayWCY6B1hIcnI93kMGMKolYu3bt+OrVq7cT0WnKAa621r5ZWUOdjncQNUJ9gZXyDnIsCWPMFcx8oZLO7WNjY1O7du3ar6wTnA5BgtHFS1yJgng6IvISIvqMhpRz7v7+eYZf0tQJzYUgoeQi5q1UQTyi/u+4dhJRR4PMOfe6PM8/rKkRkgtBQqhFzlnJgnhUp59++hMOHDhwCxH9kgYdM78/y7K3aGqUzYUgZYlVEL/SBXkMmYj"
			                                        "4s9X9Geua6/bx8fEtO3fu/I6mSNFcCFKUVIVxbRHEIzTGvJSZ/1aJ8z6/L7HWfllZZ2A6BBmIqPqANgnSl2RD/5i3NRq6/lfFeZ7foKkxKBeCDCJUw7+3TRCPdHJy8od7vZ4/Rfe5GsTMfFWWZdo/Jy85BQii6U6k3DYKcsy+5GIiukSJctvc3NyWPXv2fFdZZ0E6BIlNNKBemwXxuNI03eKc+1QAumNT9vUP89mhrDMvHYLEpBlYq+2CeGzdbvfUJEk+R0Q/GojxsbRzrbUfUdY4mg5BYpFU1IEgR+BNTEw8sdPp/BUR/boCJznnrsrzPMq+BIJoOhEpF4LMBykiFxHR+5R4b5ubm5vS7ksgiLILMdIhyEKKIvJyIvqkku+9SZJMzczM3BFaB4KEkouYB0EWh9l/TvA/EtFTlbhfa639aEgNCBJCLXIOBFka6MaNG094+OGH/ab7pRrszrkr8zx/a9kaEKQssQriIchgqGmavss5957BkUtHMPOtBw8enNq9e/eBonUgSFFSFcZBkGJwI933vrf/PK6vFBkVghShVHEMBCkO2Bjz80T0KcXpvIcHY+Zzsiwb+PA7CFK8N5VFQpByaNM0fXKv1/sAM/9WucwF0VdYa9+2XA0IoiQcIx2ChFEUEfXvuJxztzjnpmZnZ7+32CwgSFhvomZBkHCcaZq+0jn3ifAKhzO/2d+XfPX4OhBESTZGOgTRUex2u7+YJIk/DWtCU4mZz86y7KZja0AQDdFIuRBED3L9+vU/tmrVqq0R9iWXW2vf/tiMIIi+N+oKEESN8GgBY8ylzPxuZcWb+z9R+T4EUZKMkQ5BYlB8vIaIvIqIPqapyszf8PsSZl6wL1mi7nZr7WbNmHXm4tGjddIewbEmJydP6/V6H/J399Y0PQhSFWi8g1RDdt26dU8ZHx/f6px7RTUjzKsKQaqCDEGqInukrjHmPcz8rmpHIQhSFWAIUhXZx+saY85iZv+n4KouCFIVWRH5eyJ6UZH6SZKcrrkBqMgYKzVG"
			                                        "RJ5FRFuJaGMFa4QgFUA9XFJE/O+B/rxI/V6v9/TZ2dm9RWIRs5DA5OTkT/R6PS+Jv2Mx5gVBYtI8tpaI+Ien3Vag/r5er3fy7OzswQKxCFmGgIj4e979ve+xLggSi+RidUTEnxd+xoAxgm8drXLuTa3dP+/d34ob42sBCFL1C0FE/MPTtiwxzlnW2o9XPYe21e92u2f4n6g457RHWUOQOl48/W+B/clMm5j5PuecP4f8uizL/CE0uCog0O12fypJEr8vWeo/pyKjQpAilBDTXALK80sgSHNbj5kXJSAi5xDRtUS0umhOPw6ClASG8IYSSNP0TOec/8i1ocQSLrLW+hO0GnHF+KtEIxaKSVZDYGJi4sROp+MlKfQ8Lufcc/I8/0I1s4lfFYLEZ9rKisaYP2Hm3x+w+JlDhw6dUeZ5W8OGCUGG3YEVNL4x5twkSS51zp24yLK2dTqds6enp/157o25IEhjWtWMiZ5yyilPeuSRRy4gogucc4eYeZaI8v3791+8b9++HzRjFY/PEoI0rWOYb60EIEituDFY0whAkKZ1DPOtlQAEqRU3BmsaAQjStI5hvrUSgCC14sZgTSMAQZrWMcy3VgIQpFbcGKxpBCBI0zqG+dZKAILUihuDNY0ABGlaxzDfWglAkFpxY7CmEYAgTesY5lsrAQhSK24M1jQCEKRpHcN8ayUAQWrFjcGaRgCCNK1jmG+tBCBIrbgxWNMIQJCmdQzzrZUABKkVNwZrGgEI0rSOYb61EoAgteLGYE0jAEGa1jHMt1YCEKRW3BisaQQgSNM6hvnWSgCC1IobgzWNAARpWscw31oJQJBacWOwphGAIE3rGOZbKwEIUituDNY0AhCkaR3DfGslAEFqxY3BmkYAgjStY5hvrQQgSK24MVjTCECQpnUM862VAASpFTcGaxqB/wcEX90yIAjjsAAAAABJRU5ErkJggg==\"/></p></body></html>\n"
			                                        "                ", None))
		self.label_next.setText(
			QCoreApplication.translate("Form_Main", u"<html><head/><body><p><img width=\"30\" height=\"30\"\n"
			                                        "                    src=\"data:application/octet-stream;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAYAAACtWK6eAAAAAXNSR0IArs4c6QAAERVJREFUeF7tnXusZVV9x39r3zvMTVDRSl8+sGkmzOTstU/GDOGNHUpBwWhbWm2xPkDQkWLv4INYQ3hKiK0i0laKT9pYX4BIULGWRMeURmt7ncvZv3WGmYx2YkuIdmooTs1cvHevZpFzYa4zc+8+67fOPmuf9d3JhD/u+v32+n1++8M56+yXImwgAAJHJaDABgRA4OgEIAiODhBYhQAEweEBAhAExwAI+BHAJ4gfN0QlQgCCJNJolOlHAIL4cUNUIgQgSCKNRpl+BCCIHzdEJUIAgiTSaJTpRwCC+HFDVCIEIEgijUaZfgQgiB83RCVCAIIk0miU6UcAgvhxQ1QiBCBIIo1GmX4EIIgfN0QlQgCCJNJolOlHAIL4cUNUIgQgSCKNRpl+BCCIHzdEJUIAgiTSaJTpRwCC+HFDVCIEIEgijUaZfgQgiB83RCVCAIIk0miU6UcAgvhxQ1QiBCBIIo1GmX4EIIgfN0QlQgCCJNJolOlHAIL4cUNUIgQgSCKNRpl+BCCIHzdEJUIAgiTSaJTpRwCC+HFDVCIEWiOI1vrNRPR7RPQq1xtr7Z4sy+4ry/I9ifQKZY6BQCsEKYris9bai47C594sy7b3er3/GgM/7HLCCUQviNb6OiK6fo0+lNba7caYb054v1BewwSiF6QoCrbW5jW4LCiltpdl+dEaYzEEBGoRiFqQTZs2/cb09PR/1KrkmUG3MPO7h4zBcBA4IoGoBdFabyWiob82KaXun5qa2j4/P78PfQcBCYGJFGQA5BEi2s7M/yQBhNi0CUyyIK6zS4PF+0fSbvNoq9dan0dEXSI6Qym1p6qq7xpjvjjavTaT"
			                                        "fdIFWaZ4GzNf2QzSdPaS5/kGpZT7lfH1R6h6h7X2VmPM/W0mkoog7sTi14ho1hizt80Ni2nueZ4/oJQ6f5U5/YSITmbm78c072HmkowgAyh7Bz8FPzAMJIw9nEDN81Mu8EvMfGFbGaYmyHKfrmTm29ratBjmrbX+JBG5y3/W2p5g5uPWGhTr31MVxPXjdma+ItbGxD4vrfXXicgtztfclFInlWU5t+bACAekLIhrx4NZlm3r9XrDnoyMsJXNTklr7c5PufNUdbazmXlHnYGxjUldEFJK7XPrkl6v1+pfW5o+sCBI08SPsD/fM+meU7+KmT/oGZtcGASJoOVDCuJ+mbpAMm1r7ceMMdskOVKJhSARdHpIQdwl8ccS0VXCqe+oqupN/X7/h8I8Ex0OQSJo77CCMPMNnU7n4izL7hRO/9HBJSoTcbmEkMURwyHIKKgOmdNHELeLTqdzcpZldxHRS4bc5YrhSqn3lmX5fkmOSY2FIBF01lcQN/Vut3vs0tLS3WtcClGnyjuZuc4JsTq5JmYMBImglRJBlqevtf4AEUlvoHooy7KLcN/7MwcFBJkQQVwZRVFcYq39lLCkH1lr326MuUeYZyLCIUgEbQzxCbJcxmBdcjcRnSApzVp7rTHmfZIckxALQSLoYkhBBov3Zyml7gqwLvk0M78xAkRjmwIEGRv6Fd9zh7kn/Xr3M2+daWut3Rnzd9UZu8qY7ywtLV24a9eux4R5WhkOQSJoW+hPkENLGjyp0V2yLdncDUGXMfOXJEnaGAtBIujaKAVx5XW73VOqqnLrkhdLyrXW3miMcbeeJrNBkAhaPWpBXIkbN2589jHHHHOXtfYVkpKVUp8ry/J1khxtioUgEXSrCUGWy8zz/Bal1DuFZc9lWXZBr9f7sTBP9OEQJIIWNSmIK1drfSkRfUJY+hPW2je0/WkeazGAIGsRauDvTQsyWJecWlWVu45LtC4hopuZ+eoGMI1lFxBkLNhX7nQcgrgZbNiw4TkzMzNOkpdLMFhr7zHGv"
			                                        "EaSI9ZYCBJBZ8YlyCHrkg8ppd4hRPHw4uLiOY888sj/CPNEFQ5BImjHuAUJuC75GRG9lpm/GgHWIFOAIEEwypLEIIiroCiK06y17ivXiyQVKaVuKsvyGkmOWGIhSASdiEUQh2LLli3HLSwsOElqPQtqFXz3MfPvR4BXNAUIIsIXJjgmQZYrKoriVmut6EHYSikzNTV15vz8/ONhSDWfBYI0z/ywPcYoiJtknueXKaU+LkT0c2vtq40x/yjMM5ZwCDIW7Ct3Gqsgg8X76UTkvnK9UIjqBmZe6yWlwl2ED4cg4ZkOnTFmQVwxmzdvfu7i4qKT5Nyhi1sZ8BVmfur9723ZIEgEnYpdkGVEWusPu9e9SZBZa/csLi6etHv37p9K8jQVC0GaIr3KftoiyGBd8hal1MeE2Kw7e8/MDwrzjDwcgowc8do7aJMgA0nOcM/jsta+YO3qjj5CKXVtWZZR3/cOQSQdDhTbNkFc2UVRPG9wUvF3hBgeYOZXCnOMLByCjAxt/cRtFCTkuoSIfrB+/fpibm7OXaoS1QZBImhHmwUZfJq81Vr7USlKa+05xphvSPOEjIcgIWl65mq7IK7sTqdz5uA5wb/uiWE57GpmvlmYI1g4BAmG0j/RJAgyWLz/kjupqJQ6x5/GU5FfZuZXC3MECYcgQTDKkkyKIIesS9ybdWdlVOiHBw8ePHHv3r0LwjyicAgiwhcmeNIEGaxLtllr75ASUkptLcvyW9I8vvEQxJdcwLhJFGSwLjlrsC75NQkupdSfl2X5F5IcvrEQxJdcwLhJFcQh2rRp0/OnpqbcuuS3hcjGcn8JBBF2LUT4JAtyyLrkr4joz4S8Hjv++ONP2LFjx6IwT+1wCFIb1egGpiCIo6e1fhsR/a2UZFVVZ/X7/YekeerEQ5A6lEY8JhVBBov3lw0uUflVIdZG3vcOQYRdChGekiDL65Lp6Wn3MO2zhfy+yMx/KMyxajgEGSXdmrlTE2QZS57nf62UentNTEcb9igzu6dDukvog28QJD"
			                                        "jS4ROmKshgXXI5Ed0+PLWVEUqp08uy/LY0zy/GQ5DQRD3ypSzIYF3yW4N1ya944Hs6xD21vizLWyU5IEhIeoFypS6Iw3jiiSce795fIl2XhL4iGJ8ggQ5ySRoI8gy9oij+xlp7hYDn/izLzu71eizI8XQoBAlBUZgDgqwEmOf5nyqlPuKLNeRXLQji24WAcRDkcJgDJu4r1y8Pizrka+IgyLD0RzAegoQVxFr7d8aYS0K0CoKEoCjMAUHCfsUiosuZWXypvZsVBBEe3CHCIUjQRfqBqqpe1u/3dwbqzTeJaGvNXGcz846aY6MapqKazS9MBoKE+5lXKbWtLEvpg+3wK1ZMwqQuSFEUQU4UWmvfaYzBiUKPgxufIB7QmgjRWge51KSqqlP7/f6/hp4z1iChiXrkS/UTJMTFitbafcaY38TFih4H3iEh+ASR8QsaHeqyEiL6DDO/PujkDl8fYpE+SsB1cqf0CVIURZAbptzlKMYY8VXAa/UHX7HWItTA31MRJOAtty/t9/vzDbQG50GagLzWPlIQRGsd4qENu5k5J6KltZiG+js+QUKRFOSZZEHcY3/WrVvn3iUifezPncz8ZgFmr1AI4oUtbNCkCtLtds+qqspdcCh6cBwRXcbMnwxLvV42CFKP00hHTaIgRVEEefSoe3A8M+8aaQNWSQ5BxkX+kP1OmiCB1hu99evXnzQ3N/fzcbYIgoyT/mDfkyJInuehXn9wBzO7M+xj3yDI2Fvw1CXV7mpRd0KqznY9M99QZ2CTYwK+QOeNzPzpJue+2r4gSASdaLsgRVEEeQVbVVW63++bCFry9BQgSATdaLMgWusQL8v5t6qqzuz3+09G0I4VU4AgEXSkjYIEfA30bcx8ZQRtOOIUIEgEnWmbIHmen+FejGOtfYEQ3x8xsztPEu0GQSJoTZsEyfP8LUop6R17NsuybqhnV42yhRBklHRr5m6LIFrrDxPR9pplHW3YQwcOHDh33759B4V5GgmHII1gXn0nsQuyefPm5y4uLrq"
			                                        "vQudKcCml/rIsy/dIcjQdC0GaJn6E/cUsiNb6dPfucyJ6oRDVHzDzvcIcjYdDkMaRH77DWAUJtN5wX6VOYeZeBKiHngIEGRpZ+IAYBSmK4lZrrejnV2vtN2ZmZl41Nzf3s/DUmskIQZrhvOpeYhJky5Ytxy0sLLivVOdJ0Fhr32eMuVaSI4ZYCBJBF2IRpCiK0wYvsnmRBEuWZa/p9Xr3SHLEEgtBIuhEDILkeX6ZUurjQhz/W1XV1qbuFxfOtVY4BKmFabSDxi1InucfUkq9Q1KltfZr1trX9vv9A5I8scVCkAg6Mi5BNmzY8JyZmRm33ni5BIO19hpjzE2SHLHGQpAIOjMOQbrd7qlVVbl3lYvWG0QU/fVUkhZDEAm9QLFNC6K1vpSIPiGc/o+zLDu/1+t9T5gn6nAIEkF7mhQkz/Nb3Dv8hGXfd/DgwTft3bv3CWGe6MMhSAQtakKQjRs3Ptu9Ztla+wpJyZO83jgSFwgiOVoCxY5akG63e8pgvfFiyZSttRcZYz4vydG2WAgSQcdGKYjW2j2NUPrQtf8koguZ+d8jwNXoFCBIo7iPvLNRCaK1/iARvUtY4hemp6ffNj8//7gwTyvDIUgEbQstSKfTeZZS6i6l1PmS8pRS15VleaMkR9tjIUgEHQwpSKfTOcXdL05EJ0hKs9b+iTHms5IckxALQSLoYihBiqK4xFr7KWFJ36+q6nX9fv+7wjwTEQ5BImhjCEG01h8goncLy/mMtXbWGPMTYZ6JCYcgEbRSIki32z12aWnpbul6g4huYObrI8AR1RQgSATt8BWk0+mcPFhvvERYxhuY+R+EOSYyHIJE0FYfQTqdzsVZlt0pnH4/y7JLe73ed4R5JjYcgkTQ2mEFIaJjiegqydSVUp9bWFiY3bNnz35JnkmPhSARdHhIQR4gogsk07bW3miMuU6SI5VYCBJBp4cURDrjqN6/IS1m1PEQZNSEa+RvQhCl1E4iuqIsy2/XmBKGDAhAkAgOhQYE+fy6detmd+7c+d8R"
			                                        "lNuqKUCQCNo1SkGUUjeVZXlNBGW2cgpFUbiHUdS6h6aqqpe29YkuKubujEoQa+3Fxpi/j7n22Oemtb6DiLbVmOfjzPy8GuOiHJKaIN8bXDLyL1F2o0WT0lq7X/vWvMJAKXV/WZa/26LSVkw1JUHclbyzzPyjtjYrtnkXRcHW2nyNeZ3AzO7GslZuqQhyMzNf3coORT5prfXXj/K8Yvc/ovPa+vT6ZeyTLsiiUuqtZVlKLz2J/DAd7/QGX7dOIyL37wdKqR1PPvnktbt37/7peGcm3/skCzKfZdlsr9f7ZzkmZEiVwEQKopS6Z3FxcXbXrl2PpdpY1B2GQNSCbN26dXr//v3/R0TH1C3XWvt+Y8x7647HOBBYjUDUgriJa62/QkSvrNFG97Ym9yuV9FE+NXaFIakQaIMgdX5v7ymlZsuy/FYqjUOdzRCIXpDBp8jlRHT7UZDcOzU1Nfvwww8/2gwy7CUlAq0QxDUkz/M/du/rUEq5E1MdInrQScPM7r/YQGAkBFojyEiqR1IQWIMABMEhAgKrEIAgODxAAILgGAABPwL4BPHjhqhECECQRBqNMv0IQBA/bohKhAAESaTRKNOPAATx44aoRAhAkEQajTL9CEAQP26ISoQABEmk0SjTjwAE8eOGqEQIQJBEGo0y/QhAED9uiEqEAARJpNEo048ABPHjhqhECECQRBqNMv0IQBA/bohKhAAESaTRKNOPAATx44aoRAhAkEQajTL9CEAQP26ISoQABEmk0SjTjwAE8eOGqEQIQJBEGo0y/QhAED9uiEqEAARJpNEo048ABPHjhqhECECQRBqNMv0IQBA/bohKhAAESaTRKNOPAATx44aoRAhAkEQajTL9CEAQP26ISoQABEmk0SjTj8D/AxSx4TJqlBrOAAAAAElFTkSuQmCC\"/></p></body></html>\n"
			                                        "                ", None))
		self.tabWidget_main.setTabText(self.tabWidget_main.indexOf(self.tab_player),
		                               QCoreApplication.translate("Form_Main", u"\u64ad\u653e", None))
		self.label_title_search.setText(QCoreApplication.translate("Form_Main",
		                                                           u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:600;\">\u641c\u7d22</span></p></body></html>",
		                                                           None))
		self.lineEdit_search.setInputMask("")
		self.lineEdit_search.setText("")
		self.lineEdit_search.setPlaceholderText(QCoreApplication.translate("Form_Main",
		                                                                   u"\u8bf7\u8f93\u5165\u8981\u641c\u7d22\u7684\u97f3\u4e50\u540d\u5e76\u56de\u8f66",
		                                                                   None))
		self.label_search_music.setText(
			QCoreApplication.translate("Form_Main", u"<html><head/><body><p><img width=\"20\" height=\"20\"\n"
			                                        "                    src=\"data:application/octet-stream;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAYAAACtWK6eAAAAAXNSR0IArs4c6QAAGi5JREFUeF7tXQuYHUWVPqfvHWYSCQhJXFTEVcY8blXfEIKyQGQDIsjDBxDBb9EVxfeusOoi+NpF0cVVcNeNioiiq8i6oiQ+WCQLElSMug7J3D59JxMDPkDEOCCIhiRzp89+x6+DATPMrerH7e5b9X3zTfg459Sp//Q/1VVddQ6Caw4Bh8C0CKDDxiHgEJgeAUcQ93Q4BB4HAUcQ93g4BBxB3DPgELBDwM0gdrg5rT5BwBGkTwLthmmHgCOIHW5Oq08QcATpk0C7Ydoh4Ahih5vT6hMEHEH6JNBumHYIOILY4ea0+gQBR5A+CbQbph0CjiB2uDmtPkHAEaRPAu2GaYeAI4gdbk6rTxBwBOmTQLth2iHgCGKHm9PqEwQcQfok0G6Ydgg4gtjh5rT6BAFHkD4JtBumHQKOIHa4Oa0+QcARJIVAL1q0aC4AzB0YGJjLzPKzv+d58ns2Ik5EUTSBiPd5njfR6XQmZs2add/IyMhkCl07Exkj4AjSBcDNZvNAADiUmQ8CgKft+g0Af/zvLkzsSWQrAPwCAO6Kf/74b8/z2q1WiyxtOrWUEXAEmQZQrfXzAeAEAJDfzZRxn8ncTwHg6wBw0+Tk5K3j4+MPzaTg/n82CDiCxLgODw8PDg0NvQQATgKA5wHAU7OB3NjqHwBgLTPfXK/X14yOjv7S2IJTsEag7wnSaDSWI+KpiCjkeKY1kvkoykyyGhFXB0GwJp8u+7uXviRIo9E4qFarrWTmUwFgeUkfgU1CFgC4joh+XNIxFN7tviKI7/tHAMBZzHwWADyx8NHp0kFm/orneV90s0qXgBmI9QVBms3myiiKhBTyGlXl"
			                                        "tp6ZvzgwMPDFjRs3PlDlgeY1tkoTRGt9BgCcDwCH5QVoQfqRLeNVRHRpQfwprRuVJEiz2VzIzO9g5leWNjLpOH4LAHyQiNamY67/rFSOIL7vv5WZLwSA+f0XzmlH/FEAuISIfu0wMUOgMgTRWh/JzO9DRPmG4dqfI/ATALiYiL7gwOkegUoQRGv9BgD4MADs3f3QM5P8HTPfj4j3A8DDADBPzmnFvzPr1MDwpUQk6zLXukCg1ARpNBp7e54nxBCC5NXuBYAxAJDzUqPMvCkmw/2Dg4P3P94hxAULFswbGhqaOzU1Na9Wq82NomgeM89DRDnKIl/w98tpELImOZ+IWjn1V9puSksQeaWKZw35nWW7EQBuFiLUajVqtVpyTiqTJmNCxBOZWchyaCad/MmorEeEJO6V63GALiVBfN9/KTNfleEr1a0AcD0zXx+GYTvjB3WP5n3fXwQAxzGzrKmOB4DZGfnxASJ6d0a2S2+2dASJyfHlDJC/HRHXIOL1rVbr9gzsW5tcunTp/E6ncyozvw4Allkbml7xCiLK8zU1gyFkY7JUBMmIHD9l5lXz589ftW7duk42MKdn1ff912VElK8S0cr0PK2GpdIQxPf9V8WvVWkh/4AQY6+99lq1YcOG36RlNC87GRFlHREdk9cYytBPKQiitf5nALgoLUCZ+eO1Wm1Vq9UaT8tmr+xkQBRHkt2CWXiCpEkOZr4mJsYPevVAZ9VvTJRLAGD/pH0ITmEYyuHOvm+FJkiK5FiPiBcHQXBDlSPeaDQOr9VqH2Xmw5OOk5k/GIbhO5LaKbt+YQmilHoLIn4kBYA/vX379rdt2bLldynYKoUJrfXVcu8lBWcvIqL3pmCntCYKSRCt9SsA4PNJUWXmt4Rh+O9J7ZRRP8XZt69JUjiCxF/I5et10nNVxxPR/5bx4U7L50ajsdTzvJtSWJe8kYg+mZZfZbJTKILEZ6uEHEmOj9wxOTl59Pj4+D1lCkSWvmqt5eyVpC+ybb+XFEhE9H1bA2XVKxRBt"
			                                        "NaXJzx4uJqITitrMLL0W2v9fgB4V4I+vh9F0QntdlvI0jetMASJj6wLQWxbX78rdwNaCn+APklEb+ymr6rIFIIgSdcdzPy1MAyrnpAhlWdOay3n2F6awFhfrUeKQpAk78ijRHRIgoD3narv+3J8/1ibgTPzRL1eP2p0dHSzjX7ZdHpOEK21TNmfsATuLiKSBNKuGSCwcOHCOQMDA98FgCUGao+IIuKVQRDIyeLKt54SZPHixU+u1Wrfs0z5KTlrn01EcrvPNUMElixZsmBqaupmAJDM9cYNEU8OguB/jBVLptBTgiilLkPEt1pidiYRZXEvxNKd8qlprVcAgDzksyy8v4WIrF7TLPrqmUrPCCJJoz3Pk2nepr2JiJLseNn0WUkd3/fPZubPWg7uPCL6D0vdUqj1jCBKqa8h4ossUHo3EX3AQs+pTIOA1lqO9cjxHtN219TU1OFjY2O/MlUsi3xPCKK1PgUAvmEBUl9M6xa4JFJRSg0j4jrLmiiV/v7UK4JI9aQXWkT1hUT0TQs9pzIDAvF9kitMgULEezqdzmFVnUVyJ4jt7IGI/xkEwdmmAXTy3SOgtf4SAJzZvcYjkpWdRXpBEJvZQ7Z0j3SJziweXQMVpVQjftUyymtc5VkkV4LYzh7MfHEYhv9kEGsnaomA7/t/L8ksLNQrOYvkTRCbm25j9Xr9SFcQxuKRtVTRWl8HAFKezqRtIaJnmSiUQTY3giil9kdEyTBulFSAmV8bhuGnywBmVXxUSj0bEX9kOh5EPKlq9/5zI4jv+1IbUGYQk3YjEb3ARMHJpoOA1vpbcZ14E4NS1epcE4Wiy+ZGEJtEAoh4VhAE1xQdxCr6p5R6LSJ+ynBslXvNyoUglq9XW+v1+kK39jB8RFMSj2MWAsABJiar9pqVC0FsXq+Y+XNhGL7KJDhONl0EfN//GDP/naHVSr1m5UIQrbWUKjB62Jn5pWEYfsUwOE48RQSUUscg4rcNTY4TkZRuqETLiyBbAOBgA8TunjNnzoL169dLCT"
			                                        "PXeoiA1lru6xxl4oLneUe0Wq1KpHfNnCCNRuM5nuf90ARgAHD1KgwBy0rcMsNlZU5cZ06QuCzzZSYBZOYXh2EoR1Jc6zECjUbjIM/zZLHedSI/Zr45DMPjeux6Kt1nThCl1M2IaHLz7E4iWgAAU6mM0BlJjIDWejUAmGSNibZv3z57y5YtOxJ33mMDmRKk2Ww+IYoi00RjldoF6XF8U+leay0X1N5paKwSVxMyJYjv+ydJIUwTYJn5lWEYJk5cbdKnk318BGy26aUCMRG9vezYZkoQrfXbAOBSE5A8z1tWtCKaJv5XUVYptQQRNxqO7RtEZHOl2rCbbMWzJogcMjzHYAjboijar91u7zTQcaI5IKC1fhAA9jHoqhLHTrImiOke+g+I6AiDIDjRnBDQWq8HgL8y6W5wcHCvkZGRSROdoslmTZD7TI63M/OVYRj2Rca+oj0IM/mjtf4MALx6JrnH/P8lZb8FmhlBtNZ/AQD3mgCKiG8OguBjJjpONh8EtNZvBgDTHFgvI6L/zsfDbHrJkiCSte8WE7cRcUUQBLea6DjZfBCwTPRX+mu4mRHE9/0Tmdkod2un05m3adMmeS1zrWAIxNW/HjJxCxE/FATBBSY6RZPNjCBKqdMR0eQ0rsvUXrSn4zH+aK1ld3HAwM3Sf/TNjCBa65cDwBcMwPwOEf21gbwTzRkBrbWciniCQbefIaLXGMgXTjQzgphe2WTmH4ZhaLSNWDg0K+6Q1tpoVxIRrwmCII167T1DNjOCaK3PA4Cua5Qj4oYgCA7tGRKu4xkR0FpLkmqTK7hriMg0fdCMfuQpkBlBfN+/kJkvMRhMm4iUgbwTzRkBrfXPAcCkolfps9JkSZD3MPP7DGJ4BxENG8g70ZwR0FpLXcKuk8PJdd0gCJ6Xs5updpcZQSwOKrpdrFRDm74x3/eJmU1m+W8SkU0W//Sdt7SYJUFMi3NuJSL5+u5aQRFQSt2OiEsN3PsyEdlkizfoIlvRzAjSaDTO9jzPpLTXg0T0xGyH66w"
			                                        "nQcD0wGIVUjdlRhCt9RkAYHIOZzsR2RSTTBJzp2uAgNZajgEdbaByORG9yUC+cKJZEsS0zFpERLXCIeQcegQBrfVdhmWjLyOifywzhJkRRCl1LCJKHe6uW61WWzg6Oio7Ja4VDIGlS5fOn5yc3GriVhXqumRGEN/3n8nMdxgC+jdhGP6XiY6TzQcBrfXzAWCtYW/nEJFk1Sxty4wggojF4bbST8mlfRJmcFxrfT4AfMhkfMy8PAzD20x0iiabNUEC4YnBoNcR0TEG8k40JwRsaqnv3Llz/ubNmydycjGTbrImiBx3P93A84eIyCQxgIFpJ5oEAa31jwFgmYGNCSIyKgZqYDs30awJ8n4AeJfJaKIoOrTdbm8w0XGy2SIwPDw8ODQ09FsAMNmGv42IlmfrWfbWsybIKwDAKAkcIr46CAKTD4zZo9TnPVgmIL+KiExSPhUS5UwJ4vu+z8wtw5GX/haa4XgLL+77/tnMbPpH6zwiMk3yUDgsMiVIvJP1CwB4WrcjZ+bvhmFo8rW2W9NOzhIBrfXHAcDoi7gcagzDsG3ZZWHU8iDI5QDwBoMR/97zvINbrZbRRykD+07UAIH4A6GUPzBZcFfm6kLmBGk2myujKLrWICYiWonp2XDMhRRXSr0JEWUGMWmfJqLXmigUVTZzgjQajQM8z5OrmiZtPREdaaLgZLNBQGstuc0kx1nXrUrluzMniKCqlLoJEU1vlp1CREalE7qOoBPsCgGttXHyPwDY4XneQVV5Rc6FIFrrfwaAi7qKyp+EriYi2SZ2rUcIWC7ObwjD8KQeuZx6t3kR5DAA+D9D7zuI6AdBsMlQz4mngIDl4hykrnoYhp9IwYVCmMiFIPFr1ncQ8bmGoy59blfD8RZG3HJxvmNqamrh2NiYZD+pRMuTIG9HxH81RG3TvHnz/HXr1nUM9Zx4QgRsFucA8FUiWpmw60Kp50mQBiLKfrppewURXW2q5OTtEbCsSQhVPCaUG0EkXFrrbwHACYahu56I5PquazkgoJTa"
			                                        "3/O87xim9xHPfjswMLBww4YNv8nBzdy6yJUgvu+/npk/aTG6c4lolYWeUzFEQGstRVel+KpRQ8QrgyCoXHWwXAmyYsWK+sTExO0A4BuhDzARRdGKdrtt84pm2FX/ijebzedFUXSTDQKe5x3RarV+YKNbZJ1cCSJAKKX+ARH/zQKU0ichsxhzriqWH3TFx8p+s8qdIAsXLpwzMDAgs4hxHl5EfEMQBFfk+tT0SWcWqWIfQYaZjw3D0KjcXllgzZ0gAozW+h0A8C+mICHiPZ1OZ8XY2NhPTHWd/PQIKKVkh/G7JhWJd7NWua3d3ZHqCUGazeaToiiSWeSpFg9uZadzCyxSUdFayza6VaEbRDw5CAKjWpSpOJ2TkZ4QJJ5FJOPeh23GWcX9dhsc0tBJsCaUYyXXhGFoRaw0fM/DRs8IEpPk2wBgnOYHEX/GzCcR0VgeIFW1D621VH+6znJ8D3ie99xWq0WW+qVQ6zVBjgeAGy2R2ggAK4nIKHujZV+VU2s2m4dGUTRiOzBmviAMQ6NEcrZ99VKvpwSJZxGpYyj1DG2anBA+nYgkqbJrXSKwaNGiufV6Xb4p2dZjuZWIjC5Rdela4cSKQBAJkuygdF3a6zEoSmpLIcmvC4duQR2ySAL3qJEw84lhGMqxocq3nhMknkWM82c9JjK31Ov10zZu3PhA5SOWcIBKqTWI+OIEZi4lIsnT2xetEASJSSI7WklqSdw4ODh42sjIyLa+iJzFIH3f/5hcaLJQ3aWylohMD5sm6K73qoUhSEwSWbDLwt2qIeLXgyA4DQCmrAxUWElr/VEAODfBEOUV9ngiMk0EmKDL3qsWjSDNuAaF7eJR7iR8pdPpnDs2NmaaSaX30cjIA621aZb9PXnyt0T0hYxcLKzZQhEkpfWImJG9+Qv7PSuKUuoYmVUBYO+ET2BfrTt2x6pwBBHnlFKXIOKFCYMqX3rfE4ahZJjvu6aUejciXpzCwK8jIpMSFil0WRwThSRIPJPIdP7yFKBaPTU1dUE/HXDUW"
			                                        "l8JAK9Jih0z37DPPvucvn79+oeT2iqrfmEJEpPEOKvfNIGQLBsXEJFJWerSxXTx4sXPqtVqknLnuBScv4uZDwnD8P4UbJXWRKEJEpNkCwAcnAbCiPihIAguSMNWkWwsWLBg3sDAwBslSTgiPiUN32q12oGjo6O/TMNWmW0UniAxSbYDwGAaQCPiBql1EUXRZ9vt9u/TsNkrG8PDw/sMDg7uIsZfpuUHMz8rDEP5w9T3rRQESXsmiaMuD8BVMVHuLdOTcOCBB87ad999paSEzBgLUvb9KCL6fso2S2uuNASJSSJHs+WIdppNyPFZZr6qBH81a0opIYWQw6R6cDd4Peh53vKZjq/7vr+Mme/ul7NvpSKIRFkp9RFEfEs3ETeUkdetXa9ehSoi2mg0lOd5xzHzKxFxqeG4uhGXD4knT3cqWmsta0A5CiQZ+ndVIZYv6p8nosu66aCsMqUjSDyTGFfPNQzQbYj4vSiKbtuxY8faLVu27DDUTyzebDafOzU1dRwiPh8AjkhscHoD12/btu2sO++888E9icyUmZ+Zb2bm86qakqmUBIlJIq8Z8lct6VfimZ49mVmEMOsQcW2r1ZK79Km3RqOxNyK+ABGldMCJAHBA6p38ucHH/ULeaDQO9zyvm1xXbc/zzpzp9SyH8aTeRWkJEpNEqlAJSfKsRiVrFkmu1kJESWg34XneRKfTmajX6xNBEEg98T9rku5oaGjoyVNTU09h5ifH27F//C3/bVrFKeGTIAcPz5/pbJXWWo6pvLDLvqRMxZlVO8xYaoJI4OQvr+d5QhKTQqFdxtxKTE4SS37aCflh5qcgohBgjpW19JXWxuSY8VSu1lrI/kQDF8aZ+cwwDEcNdAotWnqC7EJXay0EkbXJ3EIj3lvnuj502Gg0DvE8z2az4idRFJ3RbrclZ0DpW2UIIpGIE6DJIUdXuu3Rj+atzPxBk2uyMZa2uZC3xGuSTNZrebKuUgTZBZxS6mWIKNkb5X5JP7cHmPkSm+wjUgYBEe9LAN4diH"
			                                        "hmEATWmVMS9J2aaiUJIujIMYyhoSGZTYQofdckqVutVrskyc6S1vryhGu7n0ZRdFqZX7cqS5BdjGg0GksR8RzJxggAs/qAKV9FxKvSSAcab4DINWjrXUJm/pkkiSjr7lblCbKLEL7vL2LmcwBAiLJ/BYlydXxcJtUs6/FX/C/LhmECzH7ued4pSWazBH0nUu0bguxCafHixU/3PE9mFMkp+8xE6PVe+SFE/JLMGFkWr2k2mzqKomsBYFGCIcv9kheEYdhOYCN31b4jyC6Eh4eHB4eGhl4SH36U36kcp88jgnK8AwBW1+v1NXnd2dBay4aHzCQLE4zxbjk6EwSBfFQsRetbguwenWaz+QxmPlV+AGB5QSMnD9XqKIrWtNvtH/XCR6XUEkSUmcQ2C6bkCbinXq8fMzo6urkXYzDt0xHkMYjJ6wQzHyU/ACA/vXoN24qIchBwfRRFP2q32z80DW4W8vEHRCGJcYWw3fz5FTMfXYLrBeAIMsNTpJQaljT/URQdiojyeiHv4U9L+eGTYynj8Y8cAbmlyLs+cWZ4ed1KchX6XkQ8KgiCO1PGMlVzjiAWcC5btmz2ww8/vFAIE//MZmbZQp6NiLOYebZsKSPiADNLKtRt8hsRJTvIrn9LjZPxycnJ8c2bNwtBStXii1MykzwjgeNbO53O4Zs2bfpZAhuZqjqCZApvtY0rpZ4tC3dETHIf/jdRFB3Wbrd/UUS0HEGKGJUS+dRoNJ7jeZ7MJAclcPs+z/MOabVadyewkYmqI0gmsPaX0WazeXj8nSTJ2uz+yclJf3x8/J4ioecIUqRolNgX3/ePYGZZuB+YYBi/jaKo0W63C5NlxhEkQTSd6qMR0FofyczXJkxeJ9lVFrRara1FwNcRpAhRqJAPjUZjued5MpPILUrb9rudO3ceXITdPUcQ2xA6vWkRkIws8ZrEus4LAMg5s6dPd8c/L/gdQfJCus/68X3/aHndAoAnJRj6HwYHB586MjKyx5RECex2reoI0jVUTtAUAa21lIq"
			                                        "W1635prq7yW+bnJw8YHx8/KEENqxVHUGsoXOK3SAQV7mSmSRJMo3tnufNa7Vaf+imzzRlHEHSRNPZ2iMCSqlj41PASS6q7ZgzZ85+eRfzcQRxD3UuCPi+L7mFZSYxybP1WN92bt++fZ88U8E6guTyeLhOBAGtteQZFpLsmwCRzuDg4OyRkZHJBDa6VnUE6RoqJ5gGAkqpExBRFu67ssQbm0XEqSAI5AaoZLHMtDmCZAqvM74nBJRSkqRbZpIkiceZiGoAwFmi7AiSJbrO9rQI+L5/YrwmeUISmIgo02c4U+NJBu50q4+A1vrkeE2SJF/ZtUR0RlZoOYJkhayz2xUCWutTYpIMdaWwB6F6vb7fxo0bH7DVfzw9R5AsUHU2jRBQSr0oXrhbpV6SokNBENxg1GmXwo4gXQLlxLJFwPf9F8drkgGLns4lolUWejOqOILMCJETyAsB3/dfEpOkbtJnFEWvarfbnzPR6VbWEaRbpJxcLghorU+L1yRetx12Op1nZJUZxRGk2yg4udwQUEqdHn8n6eb5vIiI3puVc904kFXfzq5DYFoEms3myiiKrpghE3+mW7zinCOIe0gLi0BcBu6dACCZ+B/VmPlTYRi+PmvnHUGyRtjZT4zAkiVLFnQ6nWWS8hURf46IW/Iq7eYIkjh8zkCVEXAEqXJ03dgSI+AIkhhCZ6DKCDiCVDm6bmyJEXAESQyhM1BlBBxBqhxdN7bECDiCJIbQGagyAo4gVY6uG1tiBBxBEkPoDFQZAUeQKkfXjS0xAo4giSF0BqqMgCNIlaPrxpYYAUeQxBA6A1VGwBGkytF1Y0uMgCNIYgidgSoj4AhS5ei6sSVGwBEkMYTOQJURcASpcnTd2BIj4AiSGEJnoMoIOIJUObpubIkRcARJDKEzUGUEHEGqHF03tsQI/D9wxGVBh99WSwAAAABJRU5ErkJggg==\"/></p></body></html>\n"
			                                        "                ", None))
		self.tabWidget_main.setTabText(self.tabWidget_main.indexOf(self.tab_search),
		                               QCoreApplication.translate("Form_Main", u"\u641c\u7d22", None))
		self.lineEdit_player_list.setText("")
		self.lineEdit_player_list.setPlaceholderText(
			QCoreApplication.translate("Form_Main", u"\u8bf7\u8f93\u5165\u6b4c\u5355/\u4e13\u8f91\u94fe\u63a5\u6216Mid",
			                           None))
		self.label_search_player_list.setText(
			QCoreApplication.translate("Form_Main", u"<html><head/><body><p><img width=\"20\" height=\"20\"\n"
			                                        "                    src=\"data:application/octet-stream;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAYAAACtWK6eAAAAAXNSR0IArs4c6QAAGi5JREFUeF7tXQuYHUWVPqfvHWYSCQhJXFTEVcY8blXfEIKyQGQDIsjDBxDBb9EVxfeusOoi+NpF0cVVcNeNioiiq8i6oiQ+WCQLElSMug7J3D59JxMDPkDEOCCIhiRzp89+x6+DATPMrerH7e5b9X3zTfg459Sp//Q/1VVddQ6Caw4Bh8C0CKDDxiHgEJgeAUcQ93Q4BB4HAUcQ93g4BBxB3DPgELBDwM0gdrg5rT5BwBGkTwLthmmHgCOIHW5Oq08QcATpk0C7Ydoh4Ahih5vT6hMEHEH6JNBumHYIOILY4ea0+gQBR5A+CbQbph0CjiB2uDmtPkHAEaRPAu2GaYeAI4gdbk6rTxBwBOmTQLth2iHgCGKHm9PqEwQcQfok0G6Ydgg4gtjh5rT6BAFHkD4JtBumHQKOIHa4Oa0+QcARJIVAL1q0aC4AzB0YGJjLzPKzv+d58ns2Ik5EUTSBiPd5njfR6XQmZs2add/IyMhkCl07Exkj4AjSBcDNZvNAADiUmQ8CgKft+g0Af/zvLkzsSWQrAPwCAO6Kf/74b8/z2q1WiyxtOrWUEXAEmQZQrfXzAeAEAJDfzZRxn8ncTwHg6wBw0+Tk5K3j4+MPzaTg/n82CDiCxLgODw8PDg0NvQQATgKA5wHAU7OB3NjqHwBgLTPfXK/X14yOjv7S2IJTsEag7wnSaDSWI+KpiCjkeKY1kvkoykyyGhFXB0GwJp8u+7uXviRIo9E4qFarrWTmUwFgeUkfgU1CFgC4joh+XNIxFN7tviKI7/tHAMBZzHwWADyx8NHp0kFm/orneV90s0qXgBmI9QVBms3myiiKhBTyGlXl"
			                                        "tp6ZvzgwMPDFjRs3PlDlgeY1tkoTRGt9BgCcDwCH5QVoQfqRLeNVRHRpQfwprRuVJEiz2VzIzO9g5leWNjLpOH4LAHyQiNamY67/rFSOIL7vv5WZLwSA+f0XzmlH/FEAuISIfu0wMUOgMgTRWh/JzO9DRPmG4dqfI/ATALiYiL7gwOkegUoQRGv9BgD4MADs3f3QM5P8HTPfj4j3A8DDADBPzmnFvzPr1MDwpUQk6zLXukCg1ARpNBp7e54nxBCC5NXuBYAxAJDzUqPMvCkmw/2Dg4P3P94hxAULFswbGhqaOzU1Na9Wq82NomgeM89DRDnKIl/w98tpELImOZ+IWjn1V9puSksQeaWKZw35nWW7EQBuFiLUajVqtVpyTiqTJmNCxBOZWchyaCad/MmorEeEJO6V63GALiVBfN9/KTNfleEr1a0AcD0zXx+GYTvjB3WP5n3fXwQAxzGzrKmOB4DZGfnxASJ6d0a2S2+2dASJyfHlDJC/HRHXIOL1rVbr9gzsW5tcunTp/E6ncyozvw4Allkbml7xCiLK8zU1gyFkY7JUBMmIHD9l5lXz589ftW7duk42MKdn1ff912VElK8S0cr0PK2GpdIQxPf9V8WvVWkh/4AQY6+99lq1YcOG36RlNC87GRFlHREdk9cYytBPKQiitf5nALgoLUCZ+eO1Wm1Vq9UaT8tmr+xkQBRHkt2CWXiCpEkOZr4mJsYPevVAZ9VvTJRLAGD/pH0ITmEYyuHOvm+FJkiK5FiPiBcHQXBDlSPeaDQOr9VqH2Xmw5OOk5k/GIbhO5LaKbt+YQmilHoLIn4kBYA/vX379rdt2bLldynYKoUJrfXVcu8lBWcvIqL3pmCntCYKSRCt9SsA4PNJUWXmt4Rh+O9J7ZRRP8XZt69JUjiCxF/I5et10nNVxxPR/5bx4U7L50ajsdTzvJtSWJe8kYg+mZZfZbJTKILEZ6uEHEmOj9wxOTl59Pj4+D1lCkSWvmqt5eyVpC+ybb+XFEhE9H1bA2XVKxRBt"
			                                        "NaXJzx4uJqITitrMLL0W2v9fgB4V4I+vh9F0QntdlvI0jetMASJj6wLQWxbX78rdwNaCn+APklEb+ymr6rIFIIgSdcdzPy1MAyrnpAhlWdOay3n2F6awFhfrUeKQpAk78ijRHRIgoD3narv+3J8/1ibgTPzRL1eP2p0dHSzjX7ZdHpOEK21TNmfsATuLiKSBNKuGSCwcOHCOQMDA98FgCUGao+IIuKVQRDIyeLKt54SZPHixU+u1Wrfs0z5KTlrn01EcrvPNUMElixZsmBqaupmAJDM9cYNEU8OguB/jBVLptBTgiilLkPEt1pidiYRZXEvxNKd8qlprVcAgDzksyy8v4WIrF7TLPrqmUrPCCJJoz3Pk2nepr2JiJLseNn0WUkd3/fPZubPWg7uPCL6D0vdUqj1jCBKqa8h4ossUHo3EX3AQs+pTIOA1lqO9cjxHtN219TU1OFjY2O/MlUsi3xPCKK1PgUAvmEBUl9M6xa4JFJRSg0j4jrLmiiV/v7UK4JI9aQXWkT1hUT0TQs9pzIDAvF9kitMgULEezqdzmFVnUVyJ4jt7IGI/xkEwdmmAXTy3SOgtf4SAJzZvcYjkpWdRXpBEJvZQ7Z0j3SJziweXQMVpVQjftUyymtc5VkkV4LYzh7MfHEYhv9kEGsnaomA7/t/L8ksLNQrOYvkTRCbm25j9Xr9SFcQxuKRtVTRWl8HAFKezqRtIaJnmSiUQTY3giil9kdEyTBulFSAmV8bhuGnywBmVXxUSj0bEX9kOh5EPKlq9/5zI4jv+1IbUGYQk3YjEb3ARMHJpoOA1vpbcZ14E4NS1epcE4Wiy+ZGEJtEAoh4VhAE1xQdxCr6p5R6LSJ+ynBslXvNyoUglq9XW+v1+kK39jB8RFMSj2MWAsABJiar9pqVC0FsXq+Y+XNhGL7KJDhONl0EfN//GDP/naHVSr1m5UIQrbWUKjB62Jn5pWEYfsUwOE48RQSUUscg4rcNTY4TkZRuqETLiyBbAOBgA8TunjNnzoL169dLCT"
			                                        "PXeoiA1lru6xxl4oLneUe0Wq1KpHfNnCCNRuM5nuf90ARgAHD1KgwBy0rcMsNlZU5cZ06QuCzzZSYBZOYXh2EoR1Jc6zECjUbjIM/zZLHedSI/Zr45DMPjeux6Kt1nThCl1M2IaHLz7E4iWgAAU6mM0BlJjIDWejUAmGSNibZv3z57y5YtOxJ33mMDmRKk2Ww+IYoi00RjldoF6XF8U+leay0X1N5paKwSVxMyJYjv+ydJIUwTYJn5lWEYJk5cbdKnk318BGy26aUCMRG9vezYZkoQrfXbAOBSE5A8z1tWtCKaJv5XUVYptQQRNxqO7RtEZHOl2rCbbMWzJogcMjzHYAjboijar91u7zTQcaI5IKC1fhAA9jHoqhLHTrImiOke+g+I6AiDIDjRnBDQWq8HgL8y6W5wcHCvkZGRSROdoslmTZD7TI63M/OVYRj2Rca+oj0IM/mjtf4MALx6JrnH/P8lZb8FmhlBtNZ/AQD3mgCKiG8OguBjJjpONh8EtNZvBgDTHFgvI6L/zsfDbHrJkiCSte8WE7cRcUUQBLea6DjZfBCwTPRX+mu4mRHE9/0Tmdkod2un05m3adMmeS1zrWAIxNW/HjJxCxE/FATBBSY6RZPNjCBKqdMR0eQ0rsvUXrSn4zH+aK1ld3HAwM3Sf/TNjCBa65cDwBcMwPwOEf21gbwTzRkBrbWciniCQbefIaLXGMgXTjQzgphe2WTmH4ZhaLSNWDg0K+6Q1tpoVxIRrwmCII167T1DNjOCaK3PA4Cua5Qj4oYgCA7tGRKu4xkR0FpLkmqTK7hriMg0fdCMfuQpkBlBfN+/kJkvMRhMm4iUgbwTzRkBrfXPAcCkolfps9JkSZD3MPP7DGJ4BxENG8g70ZwR0FpLXcKuk8PJdd0gCJ6Xs5updpcZQSwOKrpdrFRDm74x3/eJmU1m+W8SkU0W//Sdt7SYJUFMi3NuJSL5+u5aQRFQSt2OiEsN3PsyEdlkizfoIlvRzAjSaDTO9jzPpLTXg0T0xGyH66w"
			                                        "nQcD0wGIVUjdlRhCt9RkAYHIOZzsR2RSTTBJzp2uAgNZajgEdbaByORG9yUC+cKJZEsS0zFpERLXCIeQcegQBrfVdhmWjLyOifywzhJkRRCl1LCJKHe6uW61WWzg6Oio7Ja4VDIGlS5fOn5yc3GriVhXqumRGEN/3n8nMdxgC+jdhGP6XiY6TzQcBrfXzAWCtYW/nEJFk1Sxty4wggojF4bbST8mlfRJmcFxrfT4AfMhkfMy8PAzD20x0iiabNUEC4YnBoNcR0TEG8k40JwRsaqnv3Llz/ubNmydycjGTbrImiBx3P93A84eIyCQxgIFpJ5oEAa31jwFgmYGNCSIyKgZqYDs30awJ8n4AeJfJaKIoOrTdbm8w0XGy2SIwPDw8ODQ09FsAMNmGv42IlmfrWfbWsybIKwDAKAkcIr46CAKTD4zZo9TnPVgmIL+KiExSPhUS5UwJ4vu+z8wtw5GX/haa4XgLL+77/tnMbPpH6zwiMk3yUDgsMiVIvJP1CwB4WrcjZ+bvhmFo8rW2W9NOzhIBrfXHAcDoi7gcagzDsG3ZZWHU8iDI5QDwBoMR/97zvINbrZbRRykD+07UAIH4A6GUPzBZcFfm6kLmBGk2myujKLrWICYiWonp2XDMhRRXSr0JEWUGMWmfJqLXmigUVTZzgjQajQM8z5OrmiZtPREdaaLgZLNBQGstuc0kx1nXrUrluzMniKCqlLoJEU1vlp1CREalE7qOoBPsCgGttXHyPwDY4XneQVV5Rc6FIFrrfwaAi7qKyp+EriYi2SZ2rUcIWC7ObwjD8KQeuZx6t3kR5DAA+D9D7zuI6AdBsMlQz4mngIDl4hykrnoYhp9IwYVCmMiFIPFr1ncQ8bmGoy59blfD8RZG3HJxvmNqamrh2NiYZD+pRMuTIG9HxH81RG3TvHnz/HXr1nUM9Zx4QgRsFucA8FUiWpmw60Kp50mQBiLKfrppewURXW2q5OTtEbCsSQhVPCaUG0EkXFrrbwHACYahu56I5PquazkgoJTa"
			                                        "3/O87xim9xHPfjswMLBww4YNv8nBzdy6yJUgvu+/npk/aTG6c4lolYWeUzFEQGstRVel+KpRQ8QrgyCoXHWwXAmyYsWK+sTExO0A4BuhDzARRdGKdrtt84pm2FX/ijebzedFUXSTDQKe5x3RarV+YKNbZJ1cCSJAKKX+ARH/zQKU0ichsxhzriqWH3TFx8p+s8qdIAsXLpwzMDAgs4hxHl5EfEMQBFfk+tT0SWcWqWIfQYaZjw3D0KjcXllgzZ0gAozW+h0A8C+mICHiPZ1OZ8XY2NhPTHWd/PQIKKVkh/G7JhWJd7NWua3d3ZHqCUGazeaToiiSWeSpFg9uZadzCyxSUdFayza6VaEbRDw5CAKjWpSpOJ2TkZ4QJJ5FJOPeh23GWcX9dhsc0tBJsCaUYyXXhGFoRaw0fM/DRs8IEpPk2wBgnOYHEX/GzCcR0VgeIFW1D621VH+6znJ8D3ie99xWq0WW+qVQ6zVBjgeAGy2R2ggAK4nIKHujZV+VU2s2m4dGUTRiOzBmviAMQ6NEcrZ99VKvpwSJZxGpYyj1DG2anBA+nYgkqbJrXSKwaNGiufV6Xb4p2dZjuZWIjC5Rdela4cSKQBAJkuygdF3a6zEoSmpLIcmvC4duQR2ySAL3qJEw84lhGMqxocq3nhMknkWM82c9JjK31Ov10zZu3PhA5SOWcIBKqTWI+OIEZi4lIsnT2xetEASJSSI7WklqSdw4ODh42sjIyLa+iJzFIH3f/5hcaLJQ3aWylohMD5sm6K73qoUhSEwSWbDLwt2qIeLXgyA4DQCmrAxUWElr/VEAODfBEOUV9ngiMk0EmKDL3qsWjSDNuAaF7eJR7iR8pdPpnDs2NmaaSaX30cjIA621aZb9PXnyt0T0hYxcLKzZQhEkpfWImJG9+Qv7PSuKUuoYmVUBYO+ET2BfrTt2x6pwBBHnlFKXIOKFCYMqX3rfE4ahZJjvu6aUejciXpzCwK8jIpMSFil0WRwThSRIPJPIdP7yFKBaPTU1dUE/HXDUW"
			                                        "l8JAK9Jih0z37DPPvucvn79+oeT2iqrfmEJEpPEOKvfNIGQLBsXEJFJWerSxXTx4sXPqtVqknLnuBScv4uZDwnD8P4UbJXWRKEJEpNkCwAcnAbCiPihIAguSMNWkWwsWLBg3sDAwBslSTgiPiUN32q12oGjo6O/TMNWmW0UniAxSbYDwGAaQCPiBql1EUXRZ9vt9u/TsNkrG8PDw/sMDg7uIsZfpuUHMz8rDEP5w9T3rRQESXsmiaMuD8BVMVHuLdOTcOCBB87ad999paSEzBgLUvb9KCL6fso2S2uuNASJSSJHs+WIdppNyPFZZr6qBH81a0opIYWQw6R6cDd4Peh53vKZjq/7vr+Mme/ul7NvpSKIRFkp9RFEfEs3ETeUkdetXa9ehSoi2mg0lOd5xzHzKxFxqeG4uhGXD4knT3cqWmsta0A5CiQZ+ndVIZYv6p8nosu66aCsMqUjSDyTGFfPNQzQbYj4vSiKbtuxY8faLVu27DDUTyzebDafOzU1dRwiPh8AjkhscHoD12/btu2sO++888E9icyUmZ+Zb2bm86qakqmUBIlJIq8Z8lct6VfimZ49mVmEMOsQcW2r1ZK79Km3RqOxNyK+ABGldMCJAHBA6p38ucHH/ULeaDQO9zyvm1xXbc/zzpzp9SyH8aTeRWkJEpNEqlAJSfKsRiVrFkmu1kJESWg34XneRKfTmajX6xNBEEg98T9rku5oaGjoyVNTU09h5ifH27F//C3/bVrFKeGTIAcPz5/pbJXWWo6pvLDLvqRMxZlVO8xYaoJI4OQvr+d5QhKTQqFdxtxKTE4SS37aCflh5qcgohBgjpW19JXWxuSY8VSu1lrI/kQDF8aZ+cwwDEcNdAotWnqC7EJXay0EkbXJ3EIj3lvnuj502Gg0DvE8z2az4idRFJ3RbrclZ0DpW2UIIpGIE6DJIUdXuu3Rj+atzPxBk2uyMZa2uZC3xGuSTNZrebKuUgTZBZxS6mWIKNkb5X5JP7cHmPkSm+wjUgYBEe9LAN4diH"
			                                        "hmEATWmVMS9J2aaiUJIujIMYyhoSGZTYQofdckqVutVrskyc6S1vryhGu7n0ZRdFqZX7cqS5BdjGg0GksR8RzJxggAs/qAKV9FxKvSSAcab4DINWjrXUJm/pkkiSjr7lblCbKLEL7vL2LmcwBAiLJ/BYlydXxcJtUs6/FX/C/LhmECzH7ued4pSWazBH0nUu0bguxCafHixU/3PE9mFMkp+8xE6PVe+SFE/JLMGFkWr2k2mzqKomsBYFGCIcv9kheEYdhOYCN31b4jyC6Eh4eHB4eGhl4SH36U36kcp88jgnK8AwBW1+v1NXnd2dBay4aHzCQLE4zxbjk6EwSBfFQsRetbguwenWaz+QxmPlV+AGB5QSMnD9XqKIrWtNvtH/XCR6XUEkSUmcQ2C6bkCbinXq8fMzo6urkXYzDt0xHkMYjJ6wQzHyU/ACA/vXoN24qIchBwfRRFP2q32z80DW4W8vEHRCGJcYWw3fz5FTMfXYLrBeAIMsNTpJQaljT/URQdiojyeiHv4U9L+eGTYynj8Y8cAbmlyLs+cWZ4ed1KchX6XkQ8KgiCO1PGMlVzjiAWcC5btmz2ww8/vFAIE//MZmbZQp6NiLOYebZsKSPiADNLKtRt8hsRJTvIrn9LjZPxycnJ8c2bNwtBStXii1MykzwjgeNbO53O4Zs2bfpZAhuZqjqCZApvtY0rpZ4tC3dETHIf/jdRFB3Wbrd/UUS0HEGKGJUS+dRoNJ7jeZ7MJAclcPs+z/MOabVadyewkYmqI0gmsPaX0WazeXj8nSTJ2uz+yclJf3x8/J4ioecIUqRolNgX3/ePYGZZuB+YYBi/jaKo0W63C5NlxhEkQTSd6qMR0FofyczXJkxeJ9lVFrRara1FwNcRpAhRqJAPjUZjued5MpPILUrb9rudO3ceXITdPUcQ2xA6vWkRkIws8ZrEus4LAMg5s6dPd8c/L/gdQfJCus/68X3/aHndAoAnJRj6HwYHB586MjKyx5RECex2reoI0jVUTtAUAa21lIq"
			                                        "W1635prq7yW+bnJw8YHx8/KEENqxVHUGsoXOK3SAQV7mSmSRJMo3tnufNa7Vaf+imzzRlHEHSRNPZ2iMCSqlj41PASS6q7ZgzZ85+eRfzcQRxD3UuCPi+L7mFZSYxybP1WN92bt++fZ88U8E6guTyeLhOBAGtteQZFpLsmwCRzuDg4OyRkZHJBDa6VnUE6RoqJ5gGAkqpExBRFu67ssQbm0XEqSAI5AaoZLHMtDmCZAqvM74nBJRSkqRbZpIkiceZiGoAwFmi7AiSJbrO9rQI+L5/YrwmeUISmIgo02c4U+NJBu50q4+A1vrkeE2SJF/ZtUR0RlZoOYJkhayz2xUCWutTYpIMdaWwB6F6vb7fxo0bH7DVfzw9R5AsUHU2jRBQSr0oXrhbpV6SokNBENxg1GmXwo4gXQLlxLJFwPf9F8drkgGLns4lolUWejOqOILMCJETyAsB3/dfEpOkbtJnFEWvarfbnzPR6VbWEaRbpJxcLghorU+L1yRetx12Op1nZJUZxRGk2yg4udwQUEqdHn8n6eb5vIiI3puVc904kFXfzq5DYFoEms3myiiKrpghE3+mW7zinCOIe0gLi0BcBu6dACCZ+B/VmPlTYRi+PmvnHUGyRtjZT4zAkiVLFnQ6nWWS8hURf46IW/Iq7eYIkjh8zkCVEXAEqXJ03dgSI+AIkhhCZ6DKCDiCVDm6bmyJEXAESQyhM1BlBBxBqhxdN7bECDiCJIbQGagyAo4gVY6uG1tiBBxBEkPoDFQZAUeQKkfXjS0xAo4giSF0BqqMgCNIlaPrxpYYAUeQxBA6A1VGwBGkytF1Y0uMgCNIYgidgSoj4AhS5ei6sSVGwBEkMYTOQJURcASpcnTd2BIj4AiSGEJnoMoIOIJUObpubIkRcARJDKEzUGUEHEGqHF03tsQI/D9wxGVBh99WSwAAAABJRU5ErkJggg==\"/></p></body></html>\n"
			                                        "                ", None))
		self.label_title_player_list.setText(QCoreApplication.translate("Form_Main",
		                                                                u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:600;\">\u6b4c\u5355/\u4e13\u8f91</span></p></body></html>",
		                                                                None))
		self.tabWidget_main.setTabText(self.tabWidget_main.indexOf(self.tab_player_list),
		                               QCoreApplication.translate("Form_Main", u"\u6b4c\u5355\u5217\u8868", None))
		self.label_album_img.setText(
			QCoreApplication.translate("Form_Main", u"<html><head/><body><p><img width=\"100\" height=\"100\"\n"
			                                        "                    src=\"https://y.qq.com/music/photo_new/T002R300x300M000003jpkCG0OOSea_1.jpg?max_age=2592000\"/></p></body></html>",
			                           None))
		self.tabWidget_main.setTabText(self.tabWidget_main.indexOf(self.tab_album_list),
		                               QCoreApplication.translate("Form_Main", u"\u4e13\u8f91\u5217\u8868", None))
		self.label_title_player_list_2.setText(QCoreApplication.translate("Form_Main",
		                                                                  u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:600;\">\u8bbe\u7f6e</span></p></body></html>",
		                                                                  None))
		self.label_bass_version.setText(
			QCoreApplication.translate("Form_Main", u"\u64ad\u653e\u7ec4\u4ef6\u7248\u672c:{version}", None))
		self.pushButton_QQLogin.setText(
			QCoreApplication.translate("Form_Main", u"\u767b\u5f55QQ\u97f3\u4e50\u8d26\u6237", None))
		self.label_about_title.setText(QCoreApplication.translate("Form_Main",
		                                                          u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:600;\">\u5173\u4e8e MCQTSSMusic</span></p></body></html>",
		                                                          None))
		self.label_about_md.setText(QCoreApplication.translate("Form_Main",
		                                                       u"### \u672c\u9879\u76ee\u4e3a\u514d\u8d39\u5f00\u6e90\u9879\u76ee\n"
		                                                       "### \u5f00\u53d1&\u8bbe\u8ba1:MCQTSS\n"
		                                                       "#### [\u9879\u76ee\u5730\u5740:https://github.com/MCQTSS/MCQTSSMusic](https://github.com/MCQTSS/MCQTSSMusic)\n"
		                                                       "#### [\u4ea4\u6d41\u7fa4:https://t.me/+Om4thlFinuFhYzc1](https://t.me/+Om4thlFinuFhYzc1)\n"
		                                                       "#### [\u4f7f\u7528BASS\u4f5c\u4e3a\u97f3\u9891\u64ad\u653e\u6a21\u5757](https://www.un4seen.com/)\n"
		                                                       "#### \u6709\u4ec0\u4e48\u65b0\u60f3\u6cd5/Bug/\u529f\u80fd\u9700\u6c42\u90fd\u53ef\u4ee5\u5728issues\u6216\u4ea4\u6d41\u7fa4\u4e2d\u63d0~\n"
		                                                       "#### \u5982\u679c\u559c\u6b22\u8fd9\u4e2a\u9879\u76ee\u8bf7\u8bb0\u5f97\u7ed9\u4e2aStar\u6216\u5206\u4eab\u7ed9\u670b\u53cb\n"
		                                                       "### \u5173\u4e8e\u767b\u5f55QQ\u97f3\u4e50\u8d26\u6237:\n"
		                                                       "#### \u76ee\u524d\u6682\u65f6\u53ea\u652f\u6301\u901a\u8fc7QQ\u65b9\u5f0f\u767b\u5f55,\u767b\u5f55\u540eCookie\u5c06\u4f1a\u88ab\u4fdd\u5b58\u5230\u672c\u5730\n"
		                                                       "#### \u5177\u4f53\u8def\u5f84&\u5199\u6cd5\u7b49\u8bf7\u67e5\u770b\u6e90\u7801",
		                                                       None))
		self.checkBox_translate.setText(
			QCoreApplication.translate("Form_Main", u"\u5f00\u542f\u6b4c\u8bcd\u7ffb\u8bd1", None))
		self.checkBox_auto_play.setText(QCoreApplication.translate("Form_Main",
		                                                           u"\u81ea\u52a8\u64ad\u653e\u4e0a\u6b21\u64ad\u653e\u7684\u97f3\u4e50",
		                                                           None))
		self.tabWidget_main.setTabText(self.tabWidget_main.indexOf(self.tab_setting),
		                               QCoreApplication.translate("Form_Main", u"\u8bbe\u7f6e", None))
		self.label_partition_2.setText("")
		self.label_search.setText(
			QCoreApplication.translate("Form_Main", u"<html><head/><body><p><img width=\"30\" height=\"30\"\n"
			                                        "                    src=\"data:application/octet-stream;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAYAAACtWK6eAAAAAXNSR0IArs4c6QAAGi5JREFUeF7tXQuYHUWVPqfvHWYSCQhJXFTEVcY8blXfEIKyQGQDIsjDBxDBb9EVxfeusOoi+NpF0cVVcNeNioiiq8i6oiQ+WCQLElSMug7J3D59JxMDPkDEOCCIhiRzp89+x6+DATPMrerH7e5b9X3zTfg459Sp//Q/1VVddQ6Caw4Bh8C0CKDDxiHgEJgeAUcQ93Q4BB4HAUcQ93g4BBxB3DPgELBDwM0gdrg5rT5BwBGkTwLthmmHgCOIHW5Oq08QcATpk0C7Ydoh4Ahih5vT6hMEHEH6JNBumHYIOILY4ea0+gQBR5A+CbQbph0CjiB2uDmtPkHAEaRPAu2GaYeAI4gdbk6rTxBwBOmTQLth2iHgCGKHm9PqEwQcQfok0G6Ydgg4gtjh5rT6BAFHkD4JtBumHQKOIHa4Oa0+QcARJIVAL1q0aC4AzB0YGJjLzPKzv+d58ns2Ik5EUTSBiPd5njfR6XQmZs2add/IyMhkCl07Exkj4AjSBcDNZvNAADiUmQ8CgKft+g0Af/zvLkzsSWQrAPwCAO6Kf/74b8/z2q1WiyxtOrWUEXAEmQZQrfXzAeAEAJDfzZRxn8ncTwHg6wBw0+Tk5K3j4+MPzaTg/n82CDiCxLgODw8PDg0NvQQATgKA5wHAU7OB3NjqHwBgLTPfXK/X14yOjv7S2IJTsEag7wnSaDSWI+KpiCjkeKY1kvkoykyyGhFXB0GwJp8u+7uXviRIo9E4qFarrWTmUwFgeUkfgU1CFgC4joh+XNIxFN7tviKI7/tHAMBZzHwWADyx8NHp0kFm/orneV90s0qXgBmI9QVBms3myiiKhBTyGlXl"
			                                        "tp6ZvzgwMPDFjRs3PlDlgeY1tkoTRGt9BgCcDwCH5QVoQfqRLeNVRHRpQfwprRuVJEiz2VzIzO9g5leWNjLpOH4LAHyQiNamY67/rFSOIL7vv5WZLwSA+f0XzmlH/FEAuISIfu0wMUOgMgTRWh/JzO9DRPmG4dqfI/ATALiYiL7gwOkegUoQRGv9BgD4MADs3f3QM5P8HTPfj4j3A8DDADBPzmnFvzPr1MDwpUQk6zLXukCg1ARpNBp7e54nxBCC5NXuBYAxAJDzUqPMvCkmw/2Dg4P3P94hxAULFswbGhqaOzU1Na9Wq82NomgeM89DRDnKIl/w98tpELImOZ+IWjn1V9puSksQeaWKZw35nWW7EQBuFiLUajVqtVpyTiqTJmNCxBOZWchyaCad/MmorEeEJO6V63GALiVBfN9/KTNfleEr1a0AcD0zXx+GYTvjB3WP5n3fXwQAxzGzrKmOB4DZGfnxASJ6d0a2S2+2dASJyfHlDJC/HRHXIOL1rVbr9gzsW5tcunTp/E6ncyozvw4Allkbml7xCiLK8zU1gyFkY7JUBMmIHD9l5lXz589ftW7duk42MKdn1ff912VElK8S0cr0PK2GpdIQxPf9V8WvVWkh/4AQY6+99lq1YcOG36RlNC87GRFlHREdk9cYytBPKQiitf5nALgoLUCZ+eO1Wm1Vq9UaT8tmr+xkQBRHkt2CWXiCpEkOZr4mJsYPevVAZ9VvTJRLAGD/pH0ITmEYyuHOvm+FJkiK5FiPiBcHQXBDlSPeaDQOr9VqH2Xmw5OOk5k/GIbhO5LaKbt+YQmilHoLIn4kBYA/vX379rdt2bLldynYKoUJrfXVcu8lBWcvIqL3pmCntCYKSRCt9SsA4PNJUWXmt4Rh+O9J7ZRRP8XZt69JUjiCxF/I5et10nNVxxPR/5bx4U7L50ajsdTzvJtSWJe8kYg+mZZfZbJTKILEZ6uEHEmOj9wxOTl59Pj4+D1lCkSWvmqt5eyVpC+ybb+XFEhE9H1bA2XVKxRBt"
			                                        "NaXJzx4uJqITitrMLL0W2v9fgB4V4I+vh9F0QntdlvI0jetMASJj6wLQWxbX78rdwNaCn+APklEb+ymr6rIFIIgSdcdzPy1MAyrnpAhlWdOay3n2F6awFhfrUeKQpAk78ijRHRIgoD3narv+3J8/1ibgTPzRL1eP2p0dHSzjX7ZdHpOEK21TNmfsATuLiKSBNKuGSCwcOHCOQMDA98FgCUGao+IIuKVQRDIyeLKt54SZPHixU+u1Wrfs0z5KTlrn01EcrvPNUMElixZsmBqaupmAJDM9cYNEU8OguB/jBVLptBTgiilLkPEt1pidiYRZXEvxNKd8qlprVcAgDzksyy8v4WIrF7TLPrqmUrPCCJJoz3Pk2nepr2JiJLseNn0WUkd3/fPZubPWg7uPCL6D0vdUqj1jCBKqa8h4ossUHo3EX3AQs+pTIOA1lqO9cjxHtN219TU1OFjY2O/MlUsi3xPCKK1PgUAvmEBUl9M6xa4JFJRSg0j4jrLmiiV/v7UK4JI9aQXWkT1hUT0TQs9pzIDAvF9kitMgULEezqdzmFVnUVyJ4jt7IGI/xkEwdmmAXTy3SOgtf4SAJzZvcYjkpWdRXpBEJvZQ7Z0j3SJziweXQMVpVQjftUyymtc5VkkV4LYzh7MfHEYhv9kEGsnaomA7/t/L8ksLNQrOYvkTRCbm25j9Xr9SFcQxuKRtVTRWl8HAFKezqRtIaJnmSiUQTY3giil9kdEyTBulFSAmV8bhuGnywBmVXxUSj0bEX9kOh5EPKlq9/5zI4jv+1IbUGYQk3YjEb3ARMHJpoOA1vpbcZ14E4NS1epcE4Wiy+ZGEJtEAoh4VhAE1xQdxCr6p5R6LSJ+ynBslXvNyoUglq9XW+v1+kK39jB8RFMSj2MWAsABJiar9pqVC0FsXq+Y+XNhGL7KJDhONl0EfN//GDP/naHVSr1m5UIQrbWUKjB62Jn5pWEYfsUwOE48RQSUUscg4rcNTY4TkZRuqETLiyBbAOBgA8TunjNnzoL169dLCT"
			                                        "PXeoiA1lru6xxl4oLneUe0Wq1KpHfNnCCNRuM5nuf90ARgAHD1KgwBy0rcMsNlZU5cZ06QuCzzZSYBZOYXh2EoR1Jc6zECjUbjIM/zZLHedSI/Zr45DMPjeux6Kt1nThCl1M2IaHLz7E4iWgAAU6mM0BlJjIDWejUAmGSNibZv3z57y5YtOxJ33mMDmRKk2Ww+IYoi00RjldoF6XF8U+leay0X1N5paKwSVxMyJYjv+ydJIUwTYJn5lWEYJk5cbdKnk318BGy26aUCMRG9vezYZkoQrfXbAOBSE5A8z1tWtCKaJv5XUVYptQQRNxqO7RtEZHOl2rCbbMWzJogcMjzHYAjboijar91u7zTQcaI5IKC1fhAA9jHoqhLHTrImiOke+g+I6AiDIDjRnBDQWq8HgL8y6W5wcHCvkZGRSROdoslmTZD7TI63M/OVYRj2Rca+oj0IM/mjtf4MALx6JrnH/P8lZb8FmhlBtNZ/AQD3mgCKiG8OguBjJjpONh8EtNZvBgDTHFgvI6L/zsfDbHrJkiCSte8WE7cRcUUQBLea6DjZfBCwTPRX+mu4mRHE9/0Tmdkod2un05m3adMmeS1zrWAIxNW/HjJxCxE/FATBBSY6RZPNjCBKqdMR0eQ0rsvUXrSn4zH+aK1ld3HAwM3Sf/TNjCBa65cDwBcMwPwOEf21gbwTzRkBrbWciniCQbefIaLXGMgXTjQzgphe2WTmH4ZhaLSNWDg0K+6Q1tpoVxIRrwmCII167T1DNjOCaK3PA4Cua5Qj4oYgCA7tGRKu4xkR0FpLkmqTK7hriMg0fdCMfuQpkBlBfN+/kJkvMRhMm4iUgbwTzRkBrfXPAcCkolfps9JkSZD3MPP7DGJ4BxENG8g70ZwR0FpLXcKuk8PJdd0gCJ6Xs5updpcZQSwOKrpdrFRDm74x3/eJmU1m+W8SkU0W//Sdt7SYJUFMi3NuJSL5+u5aQRFQSt2OiEsN3PsyEdlkizfoIlvRzAjSaDTO9jzPpLTXg0T0xGyH66w"
			                                        "nQcD0wGIVUjdlRhCt9RkAYHIOZzsR2RSTTBJzp2uAgNZajgEdbaByORG9yUC+cKJZEsS0zFpERLXCIeQcegQBrfVdhmWjLyOifywzhJkRRCl1LCJKHe6uW61WWzg6Oio7Ja4VDIGlS5fOn5yc3GriVhXqumRGEN/3n8nMdxgC+jdhGP6XiY6TzQcBrfXzAWCtYW/nEJFk1Sxty4wggojF4bbST8mlfRJmcFxrfT4AfMhkfMy8PAzD20x0iiabNUEC4YnBoNcR0TEG8k40JwRsaqnv3Llz/ubNmydycjGTbrImiBx3P93A84eIyCQxgIFpJ5oEAa31jwFgmYGNCSIyKgZqYDs30awJ8n4AeJfJaKIoOrTdbm8w0XGy2SIwPDw8ODQ09FsAMNmGv42IlmfrWfbWsybIKwDAKAkcIr46CAKTD4zZo9TnPVgmIL+KiExSPhUS5UwJ4vu+z8wtw5GX/haa4XgLL+77/tnMbPpH6zwiMk3yUDgsMiVIvJP1CwB4WrcjZ+bvhmFo8rW2W9NOzhIBrfXHAcDoi7gcagzDsG3ZZWHU8iDI5QDwBoMR/97zvINbrZbRRykD+07UAIH4A6GUPzBZcFfm6kLmBGk2myujKLrWICYiWonp2XDMhRRXSr0JEWUGMWmfJqLXmigUVTZzgjQajQM8z5OrmiZtPREdaaLgZLNBQGstuc0kx1nXrUrluzMniKCqlLoJEU1vlp1CREalE7qOoBPsCgGttXHyPwDY4XneQVV5Rc6FIFrrfwaAi7qKyp+EriYi2SZ2rUcIWC7ObwjD8KQeuZx6t3kR5DAA+D9D7zuI6AdBsMlQz4mngIDl4hykrnoYhp9IwYVCmMiFIPFr1ncQ8bmGoy59blfD8RZG3HJxvmNqamrh2NiYZD+pRMuTIG9HxH81RG3TvHnz/HXr1nUM9Zx4QgRsFucA8FUiWpmw60Kp50mQBiLKfrppewURXW2q5OTtEbCsSQhVPCaUG0EkXFrrbwHACYahu56I5PquazkgoJTa"
			                                        "3/O87xim9xHPfjswMLBww4YNv8nBzdy6yJUgvu+/npk/aTG6c4lolYWeUzFEQGstRVel+KpRQ8QrgyCoXHWwXAmyYsWK+sTExO0A4BuhDzARRdGKdrtt84pm2FX/ijebzedFUXSTDQKe5x3RarV+YKNbZJ1cCSJAKKX+ARH/zQKU0ichsxhzriqWH3TFx8p+s8qdIAsXLpwzMDAgs4hxHl5EfEMQBFfk+tT0SWcWqWIfQYaZjw3D0KjcXllgzZ0gAozW+h0A8C+mICHiPZ1OZ8XY2NhPTHWd/PQIKKVkh/G7JhWJd7NWua3d3ZHqCUGazeaToiiSWeSpFg9uZadzCyxSUdFayza6VaEbRDw5CAKjWpSpOJ2TkZ4QJJ5FJOPeh23GWcX9dhsc0tBJsCaUYyXXhGFoRaw0fM/DRs8IEpPk2wBgnOYHEX/GzCcR0VgeIFW1D621VH+6znJ8D3ie99xWq0WW+qVQ6zVBjgeAGy2R2ggAK4nIKHujZV+VU2s2m4dGUTRiOzBmviAMQ6NEcrZ99VKvpwSJZxGpYyj1DG2anBA+nYgkqbJrXSKwaNGiufV6Xb4p2dZjuZWIjC5Rdela4cSKQBAJkuygdF3a6zEoSmpLIcmvC4duQR2ySAL3qJEw84lhGMqxocq3nhMknkWM82c9JjK31Ov10zZu3PhA5SOWcIBKqTWI+OIEZi4lIsnT2xetEASJSSI7WklqSdw4ODh42sjIyLa+iJzFIH3f/5hcaLJQ3aWylohMD5sm6K73qoUhSEwSWbDLwt2qIeLXgyA4DQCmrAxUWElr/VEAODfBEOUV9ngiMk0EmKDL3qsWjSDNuAaF7eJR7iR8pdPpnDs2NmaaSaX30cjIA621aZb9PXnyt0T0hYxcLKzZQhEkpfWImJG9+Qv7PSuKUuoYmVUBYO+ET2BfrTt2x6pwBBHnlFKXIOKFCYMqX3rfE4ahZJjvu6aUejciXpzCwK8jIpMSFil0WRwThSRIPJPIdP7yFKBaPTU1dUE/HXDUW"
			                                        "l8JAK9Jih0z37DPPvucvn79+oeT2iqrfmEJEpPEOKvfNIGQLBsXEJFJWerSxXTx4sXPqtVqknLnuBScv4uZDwnD8P4UbJXWRKEJEpNkCwAcnAbCiPihIAguSMNWkWwsWLBg3sDAwBslSTgiPiUN32q12oGjo6O/TMNWmW0UniAxSbYDwGAaQCPiBql1EUXRZ9vt9u/TsNkrG8PDw/sMDg7uIsZfpuUHMz8rDEP5w9T3rRQESXsmiaMuD8BVMVHuLdOTcOCBB87ad999paSEzBgLUvb9KCL6fso2S2uuNASJSSJHs+WIdppNyPFZZr6qBH81a0opIYWQw6R6cDd4Peh53vKZjq/7vr+Mme/ul7NvpSKIRFkp9RFEfEs3ETeUkdetXa9ehSoi2mg0lOd5xzHzKxFxqeG4uhGXD4knT3cqWmsta0A5CiQZ+ndVIZYv6p8nosu66aCsMqUjSDyTGFfPNQzQbYj4vSiKbtuxY8faLVu27DDUTyzebDafOzU1dRwiPh8AjkhscHoD12/btu2sO++888E9icyUmZ+Zb2bm86qakqmUBIlJIq8Z8lct6VfimZ49mVmEMOsQcW2r1ZK79Km3RqOxNyK+ABGldMCJAHBA6p38ucHH/ULeaDQO9zyvm1xXbc/zzpzp9SyH8aTeRWkJEpNEqlAJSfKsRiVrFkmu1kJESWg34XneRKfTmajX6xNBEEg98T9rku5oaGjoyVNTU09h5ifH27F//C3/bVrFKeGTIAcPz5/pbJXWWo6pvLDLvqRMxZlVO8xYaoJI4OQvr+d5QhKTQqFdxtxKTE4SS37aCflh5qcgohBgjpW19JXWxuSY8VSu1lrI/kQDF8aZ+cwwDEcNdAotWnqC7EJXay0EkbXJ3EIj3lvnuj502Gg0DvE8z2az4idRFJ3RbrclZ0DpW2UIIpGIE6DJIUdXuu3Rj+atzPxBk2uyMZa2uZC3xGuSTNZrebKuUgTZBZxS6mWIKNkb5X5JP7cHmPkSm+wjUgYBEe9LAN4diH"
			                                        "hmEATWmVMS9J2aaiUJIujIMYyhoSGZTYQofdckqVutVrskyc6S1vryhGu7n0ZRdFqZX7cqS5BdjGg0GksR8RzJxggAs/qAKV9FxKvSSAcab4DINWjrXUJm/pkkiSjr7lblCbKLEL7vL2LmcwBAiLJ/BYlydXxcJtUs6/FX/C/LhmECzH7ued4pSWazBH0nUu0bguxCafHixU/3PE9mFMkp+8xE6PVe+SFE/JLMGFkWr2k2mzqKomsBYFGCIcv9kheEYdhOYCN31b4jyC6Eh4eHB4eGhl4SH36U36kcp88jgnK8AwBW1+v1NXnd2dBay4aHzCQLE4zxbjk6EwSBfFQsRetbguwenWaz+QxmPlV+AGB5QSMnD9XqKIrWtNvtH/XCR6XUEkSUmcQ2C6bkCbinXq8fMzo6urkXYzDt0xHkMYjJ6wQzHyU/ACA/vXoN24qIchBwfRRFP2q32z80DW4W8vEHRCGJcYWw3fz5FTMfXYLrBeAIMsNTpJQaljT/URQdiojyeiHv4U9L+eGTYynj8Y8cAbmlyLs+cWZ4ed1KchX6XkQ8KgiCO1PGMlVzjiAWcC5btmz2ww8/vFAIE//MZmbZQp6NiLOYebZsKSPiADNLKtRt8hsRJTvIrn9LjZPxycnJ8c2bNwtBStXii1MykzwjgeNbO53O4Zs2bfpZAhuZqjqCZApvtY0rpZ4tC3dETHIf/jdRFB3Wbrd/UUS0HEGKGJUS+dRoNJ7jeZ7MJAclcPs+z/MOabVadyewkYmqI0gmsPaX0WazeXj8nSTJ2uz+yclJf3x8/J4ioecIUqRolNgX3/ePYGZZuB+YYBi/jaKo0W63C5NlxhEkQTSd6qMR0FofyczXJkxeJ9lVFrRara1FwNcRpAhRqJAPjUZjued5MpPILUrb9rudO3ceXITdPUcQ2xA6vWkRkIws8ZrEus4LAMg5s6dPd8c/L/gdQfJCus/68X3/aHndAoAnJRj6HwYHB586MjKyx5RECex2reoI0jVUTtAUAa21lIq"
			                                        "W1635prq7yW+bnJw8YHx8/KEENqxVHUGsoXOK3SAQV7mSmSRJMo3tnufNa7Vaf+imzzRlHEHSRNPZ2iMCSqlj41PASS6q7ZgzZ85+eRfzcQRxD3UuCPi+L7mFZSYxybP1WN92bt++fZ88U8E6guTyeLhOBAGtteQZFpLsmwCRzuDg4OyRkZHJBDa6VnUE6RoqJ5gGAkqpExBRFu67ssQbm0XEqSAI5AaoZLHMtDmCZAqvM74nBJRSkqRbZpIkiceZiGoAwFmi7AiSJbrO9rQI+L5/YrwmeUISmIgo02c4U+NJBu50q4+A1vrkeE2SJF/ZtUR0RlZoOYJkhayz2xUCWutTYpIMdaWwB6F6vb7fxo0bH7DVfzw9R5AsUHU2jRBQSr0oXrhbpV6SokNBENxg1GmXwo4gXQLlxLJFwPf9F8drkgGLns4lolUWejOqOILMCJETyAsB3/dfEpOkbtJnFEWvarfbnzPR6VbWEaRbpJxcLghorU+L1yRetx12Op1nZJUZxRGk2yg4udwQUEqdHn8n6eb5vIiI3puVc904kFXfzq5DYFoEms3myiiKrpghE3+mW7zinCOIe0gLi0BcBu6dACCZ+B/VmPlTYRi+PmvnHUGyRtjZT4zAkiVLFnQ6nWWS8hURf46IW/Iq7eYIkjh8zkCVEXAEqXJ03dgSI+AIkhhCZ6DKCDiCVDm6bmyJEXAESQyhM1BlBBxBqhxdN7bECDiCJIbQGagyAo4gVY6uG1tiBBxBEkPoDFQZAUeQKkfXjS0xAo4giSF0BqqMgCNIlaPrxpYYAUeQxBA6A1VGwBGkytF1Y0uMgCNIYgidgSoj4AhS5ei6sSVGwBEkMYTOQJURcASpcnTd2BIj4AiSGEJnoMoIOIJUObpubIkRcARJDKEzUGUEHEGqHF03tsQI/D9wxGVBh99WSwAAAABJRU5ErkJggg==\"/></p></body></html>\n"
			                                        "                ", None))
		self.label_player_list.setText(
			QCoreApplication.translate("Form_Main", u"<html><head/><body><p><img width=\"30\" height=\"30\"\n"
			                                        "                    src=\"data:application/octet-stream;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAYAAACtWK6eAAAAAXNSR0IArs4c6QAADhlJREFUeF7tnV+IXdUVh9c6MyOhCH3woRaM5CkZz9n3DnWCVWlAAtKHitKHCUWJiIqiBgkNQh8aVCoUIY1KHsRIFKIiGJBiKkJAfImxPkzbzN73eiVBRFQQqtKCmhkmd5dDJyD5M3fdk73OPvfs37y6zm+t9e3zee9k7h8m/IAACFySAIMNCIDApQlAENwdILAOAQiC2wMEIAjuARCoRgCPINW44apECECQRA4aa1YjAEGqccNViRCAIIkcNNasRgCCVOOGqxIhAEESOWisWY0ABKnGDVclQgCCJHLQWLMaAQhSjRuuSoQABEnkoLFmNQIQpBo3XJUIAQiSyEFjzWoEIEg1brgqEQIQJJGDxprVCECQatxwVSIEIEgiB401qxGAINW44apECEQRZHZ2dtPMzEzuvS+89zkzb2oJ7++895aZ+1mWnVpZWTk1GAy+bsluSa5RqyALCwtT/X7/WWbelQptZn7KWrs3lX3btmdtghRFUT5SvElEW9oGcdQ+3vsPN2zYsH1xcfH7UbX4780iUIsgxpjHieiJZq0eZZo559xSlM5oWomAuiBFUWxn5ncrTde+i75yzl3dvrXau5GqIPPz8zPLy8ufERFuirV7iJn3WGv3t/eWatdmqoIYYw4T0c52Ibv8bYbD4bZ+v3/88pOQoE1ATRBjzEYiKh898HMhgUPOufsBpvkENAW5lYiONR9B/RMyc89aa+rvjI7jElATpNPp7PLeHxh3oFTqsyzbuLS09Hkq+07qnmqCGGNeJCI8jbjEncHMO6y1Ryb1xkllbk1B3iOiW1IBWWHPJ5xzT1a4DpfUSACC1Aj7vFYQJB57"
			                                        "cWcIIkYVvBCCBEcaPhCChGcqTawkSJ7nV2RZttN7fwMzb5Y2a1HdN8xcPn3/wFq7qL0XBNEmfOn8sQUp3yYwPT39GhHdHG/sRnU+4Jx7VHMiCKJJd/3ssQTpdrtbhsPhIN64je28zzn3mNZ0EESL7OjcsQQxxpwgoptGx6ZX4b2/s9frva6xOQTRoCrLFAtijOkS0UlZbJJVzzvnHtbYHIJoUJVligXJ8/yeLMtelsUmWXXUOXe7xuYQRIOqLFMsSKfTuct7/6osNr0qZn7LWnuHxuYQRIOqLFMsyNzc3OazZ89+LItNsuo559xujc0hiAZVWaZYkDLOGPMGES3IotOqYuatWn8TgSDx7qWxBFmTxMcbt7Gd73bOvaI1HQTRIjs6d2xB1iTZR0R7Rse3vmKRmfdaa9/R3BSCaNJdP7uSIGVk+TvJ6urqfMIvNTmh9ZTq/CODIBMoSLyR0+sMQeKdeeVHkHgjp9cZgsQ7cwgSj724MwQRowpeCEGCIw0fCEHCM5UmQhApqYh1ECQefAgSj724MwQRowpeCEGCIw0fCEHCM5UmQhApqYh1ECQefAgSj724MwQRowpeCEGCIw0fCEHCM5UmQhApqYh1ECQefAgSj724MwQRowpeCEGCIw0fCEHCM5UmQhApqYh1ECQefAgSj724MwQRowpeCEGCIw0fCEHCM5UmQhApqYh1ECQefAgSj724MwQRowpeCEGCIw0fCEHCM5UmQhApqYh1ECQefAgSj724MwQRowpeWEmQTqczT0TlR5FeS0RXBZ+q4YHe+x+I6JMsy5astQe1x4Ug2oQvnT+2IMaYnUR0ON7Ijeu86JzbqjkVBNGku372WIIYY+4lokPxxm1s52POuV9rTQdBtMiOzhULkuf5lVmWfURE14yOTbJCzHJcOhBkXGLh6sWHaowpv5Pw/XCtW5f0knPuPo2tIIgGVVmmWJCiKHYz8zOy2CSr1J5mQZB495NYEGPMbUR0NN6oje98xDm3Q2NKCKJBVZYpFuS66"
			                                        "677+dTU1Jey2PSqvPdP93q9P2hsDkE0qMoyxYKUcUVRvMDMD8iik6r6dnV19frBYPCpxtYQRIOqLHMsQcpIYwy+QOc8tsz8oOYfDCGI7GbWqBpbkLVHkkeyLHvIe19oDDUhmV9479/Osuyg9veEQJB4d0QlQc6Nu/Z7yZZ440fr/I1zbqmu7hCkLtIX9rksQeKNnVZnCBLvvCFIPPbizpqClP9uX/77PX4uQoCZ91hr9wNOswmoCdLpdP7kvf9js9ePN91wONzW7/ePx5sAnSUE1AQpiuJ3zPy6ZIgEa5bPnDnz09OnTy8nuPtErawmSJ7nv8iy7B8TRaO+YY8757bV1w6dqhJQE2R+fv4ny8vLAyLaWHW4tl7nvd/f6/X2tHW/Nu2lJkgJqdPp7PLeH2gTsAC7fDU1NTV/8uTJLwJkIUKZgKog5ezGmGNEdKvyHhMTz8y/tdb+dWIGTnxQdUHWJMFriP5/o6m9byHx+1ht/boE6ZY3BxH9TG2Thgczc89aaxo+JsY7j0Atgpzr2el0fu+9/0tip/BfItrvnHsysb1bsW6tgpTE8jz/VZZl9zDzjS1+ReoZ7/37zPwv7/1LvV6v34q7JcElahfkx4y73e413vubvPd5G9h77//jvf+AiP7Z7/dX2rBT6jtEFSR1+Ni/+QQgSPPPCBNGJABBIsJH6+YTgCDNPyNMGJEABIkIH62bTwCCNP+MMGFEAhAkIny0bj4BCNL8M8KEEQlAkIjw0br5BCBI888IE0YkEFUQvNQk4smjtYhA7YLgxYqic0FRQwjUKghe7t6QU8cYYgK1CGKMwRum8IYp8U3ZpEJ1QdY+3eS7Ji0dcRa85TYi/Cqt1QUpiuLvzPzLKsO18Rp8aMNknaqqIPj40YveDPjYnwlyRE2Q2dnZq6anp/89QSxqGxUfHFcb6stupCZIt9u9cTgclm8/xc+FBPDRoxNyV6gJYozZSUSHJ4RD3WPiw6vrJl6xn5ogRVH8mZlVvpq34q6Nugxff9Co47jkMG"
			                                        "qCGGP+RkS/mQwM9U+JL9Cpn3mVjpqCvEdEt1QZKpFr8BVsE3DQECTeIUGQeOzFnSGIGFXwwssSBF8DHfw8LhoIQerhfLEulQQpiuKRLMseavHHtkpO5Avv/dtZlh201i5KLqhaA0Gqkrv868YWxBiDr5E4jzszP2itPXj5x3HxBAiiRXZ07liCFEXxAjM/MDo2uYpvV1dXrx8MBp9qbA5BNKjKMsWCrP2+8aUsNr0q7/3TvV5P5W9uECTe/SQWxBhzGxEdjTdq4zsfcc7t0JgSgmhQlWWKBSmKYjczPyOLTbJK7X02ECTe/SQWxBhzMxG9H2/Uxnd+yTl3n8aUEESDqixTLEie51dmWfYREV0ji06uSsxyXDIQZFxi4erHOlRjzL1EdChc+9YkqT29KglBkHj3yViClGPiLQQXHNaic26r5hFCEE2662ePLUgZ1+l05onoLu/9tUR0Vbzx43T23v9ARJ9kWbak+QfCc9tBkDjnXHatJEi8cdPsDEHinTsEicde3BmCiFEFL4QgwZGGD4Qg4ZlKEyGIlFTEOggSDz4Eicde3BmCiFEFL4QgwZGGD4Qg4ZlKEyGIlFTEOggSDz4Eicde3BmCiFEFL4QgwZGGD4Qg4ZlKEyGIlFTEOggSDz4Eicde3BmCiFEFL4QgwZGGD4Qg4ZlKEyGIlFTEOggSDz4Eicde3BmCiFEFL4QgwZGGD4Qg4ZlKEyGIlFTEOggSDz4Eicde3BmCiFEFL4QgwZGGD4Qg4ZlKEyGIlFTEOggSDz4Eicde3BmCiFEFL4QgwZGGD4Qg4ZlKEysLMjc3t3l1dXWemTdLm7Wo7htmPqH9vSDneEGQeHdOJUGMMfuIaE+8sRvTeZGZ91pr39GcCIJo0l0/e2xB8AU6FwV6t3PuFa1jhCBaZEfnjiWIMeYNIloYHZteBTNv1XrKBUHi3U9iQcrfOc6ePftxvFEb3/k559xujSkhiAZVWaZYkE6nU37U6Kuy2PSqmPkta+0dGptDEA2qskyxIHme35N"
			                                        "l2cuy2CSrjjrnbtfYHIJoUJVligUxxnSJ6KQsNsmq551zD2tsDkE0qMoyxYKUccaYE0R0kyw6rSrv/Z29Xu91ja0hiAZVWeZYgnS73S3D4XAgi06qap9z7jGtjSGIFtnRuWMJUsbNzs5ump6efo2Iyu8sxA/RAefco5ogIIgm3fWzxxakjMvz/Iosy3Z6729I+KUm7xHRB1p/+/jxsUGQCRMk3rhpdoYg8c690iNIvHHT7AxB4p07BInHXtxZU5AXieh+8SSJFTLzDmvtkcTWnrh11QTpdDq7vPcHJo5ITQNnWbZxaWnp85raoU1FAmqCGGNuJaJjFedq9WXM3LPWmlYv2ZLlNAXZSESftYRT6DUOOefw9DM0VYU8NUHKWY0xh4lop8LcEx05HA639fv94xO9RCLDqwoyPz8/s7y8XD6KXJ0Iz5FrMvMea+3+kYUoaAQBVUHKDYui2M7M7zZi2/hDfOWcw/8s4p+DeAJ1Qdaeaj1ORE+Ip2pv4Zxzbqm967Vvs1oEWXskyZn5TSLa0j6M62/kvf9ww4YN2xcXF79PbfdJ37c2QUpQCwsLU/1+/1lm3jXp4KTzM/NT1tq90nrUNYtArYKcW7182fbMzEzuvS+89+Ujy6ZmYak8zXfee8vM/SzLTq2srJwaDAZfV07DhdEJRBEk+tYYAASEBCCIEBTK0iQAQdI8d2wtJABBhKBQliYBCJLmuWNrIQEIIgSFsjQJQJA0zx1bCwlAECEolKVJAIKkee7YWkgAgghBoSxNAhAkzXPH1kICEEQICmVpEoAgaZ47thYSgCBCUChLkwAESfPcsbWQAAQRgkJZmgQgSJrnjq2FBCCIEBTK0iQAQdI8d2wtJABBhKBQliYBCJLmuWNrIQEIIgSFsjQJ/A8HFckFn/c0NwAAAABJRU5ErkJggg==\"/></p></body></html>\n"
			                                        "                ", None))
		self.label_player.setText(
			QCoreApplication.translate("Form_Main", u"<html><head/><body><p><img width=\"30\" height=\"30\"\n"
			                                        "                    src=\"data:application/octet-stream;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAYAAACtWK6eAAAAAXNSR0IArs4c6QAACo9JREFUeF7tnTusnEcVgM/cK/tKFkRCMkRxA4VlybuzloybkAhhVykSIA7pQAIUZIUSl0kRp0jKpAyKiKJI0OUFhEiufBEKCYWx5J29dgFdFF4KBdBY9t5BC7aUx927c2bn8U/ms+TKZ86Z//vP55mz64cRfkAAAksJGNhAAALLCSAI3QGBfQggCO0BAQShByAQR4ATJI4bqzohgCCdvGgeM44AgsRxY1UnBBCkkxfNY8YRQJA4bqzqhACCdPKiecw4AggSx41VnRBAkE5eNI8ZRwBB4rixqhMCCNLJi+Yx4wggSBw3VnVCAEEG8KKttY+JyDe8919fbMcY8zsR+a1z7qUBbK/rLSBIxddvrb1bRF4RkQeWbOOiiHzfOfe3itvsujSCVHz91tqfi8h3V2zhF86571XcZtelEaTS6x+Px98xxrwaUt57/+hsNnstJJaYtAQQJC3P4GzW2mdE5InABc86554MjCUsIQEESQhTk8pa+5aIPBi45jfOuYcCYwlLSABBEsLUpLLWXhKR04Frtp1zZwJjCUtIAEESwtSkQhANrXqxCFKJPYJUAq8siyBKYKnCESQVybx5ECQv36XZEaQSeGVZBFECSxWOIKlI5s2DIHn5coJU4puqLIKkIqnMwwmiBFYpHEEqgUeQSuCVZRFECSxVOIKkIpk3D4Lk5csMUolvqrIIkoqkMg8niBJYpXAEqQQeQSqBV5ZFECWwVOEIkopk3jwIkpcvM0glvqnKIkgqkso8nCBKYJXCEaQSeASpBF5ZFkGUwFKFI0gqknnzIEhevswglfimKosgqUgq83CCKIFVCkeQSuARpBJ4ZVkE"
			                                        "UQJLFY4gqUjmzYMgefkyg1Tim6osgqQiqczDCaIEVikcQSqBR5BK4JVlEUQJLFU4gqQimTcPguTlywxSiW+qsgiSiqQyDyeIElilcASpBB5BKoFXlkUQJbBU4QiSimTePAiSly8zSCW+qcoiSCqSyjycIEpglcIRpBJ4BKkEXlkWQZTAUoUjSCqSefMgSF6+zCCV+KYqiyCpSCrzcIIogVUKR5BK4BGkEnhlWQRRAksVjiCpSObNgyB5+TKDVOKbqiyCpCKpzMMJogRWKRxBKoFHkErglWURRAksVTiCpCKZNw+C5OXLDFKJb6qyCJKKpDIPJ4gSWKVwBKkEHkEqgVeWRRAlsFThCJKKZN48CJKXLzNIJb6pyiJIKpLKPJwgSmCVwhGkEngEqQReWRZBlMBShSNIKpJ58yBIXr7MIJX4piqLIKlIKvNwgiiBVQpHkErgEaQSeGVZBFECSxWOIKlI5s2DIHn5MoNU4puqLIKkIqnMwwmiBFYpHEEqge9VkKNHj24dOnToyO7u7pe99+977/+6s7Pzn0qvYWVZBFmJKE9Aj4JYa58yxpzz3h/5KFXv/fOz2ex8HtLrZUWQ9fhFr+5NEGvt6yJydh9gbzvnHowGmmkhgmQCuyptT4KMRqMfbGxsvLyKiYhccM49HRBXLARBiqH+eKGeBLHWXhWRSSDqo865PwfGZg9DkOyI9y7QiyCTyeQL3vt/KjA/4px7QxGfNRRBsuJdnrwXQay1p0XkkgLzoK5ZCKJ4cylDEWQpTQRJ2Wit5kIQBGm1d4vsG0EQpEijtVoEQRCk1d4tsm8EQZAijdZqEQRBkFZ7t8i+EQRBijRaq0UQBEFa7d0i+0YQBCnSaK0WQRAEabV3i+wbQRCkSKO1WgRBEKTV3i2ybwRBkCKN1moRBEGQVnu3yL4RBEGKNFqrRRAEQVrt3SL7RhAEKdJorRZBEARptXeL7BtBEKRIo7VaBEEQpNXeLbJvBEGQIo3WahEEQZBWe7fIvhEEQYo0WqtFEARBW"
			                                        "u3dIvtGEAQp0mitFkEQBGm1d4vsG0EQpEijtVoEQRCk1d4tsm8EQZAijdZqEQRBkFZ7t8i+EQRBijRaq0UQBEFa7d0i+0YQBCnSaK0WQRAEabV3i+wbQRCkSKO1WgRBEKTV3i2ybwRBkCKN1moRBEGQVnu3yL4RBEGKNFqrRRAEQVrt3SL7RhAEKdJorRZBEARptXeL7BtBEKRIo7VaBEEQpNXeLbJvBEGQIo3WahEEQZBWe7fIvhEEQYo0WqtFEARB1urdY8eOHT548OB57/09xpiviMifROR959zTayUeyGIEQZDoVhyPx/cbY94Wkbs+mcQY88F8Pn9kZ2fnD9EFBrAQQRAkqg3H4/HIGDNbtfjWrVuHr1+//uGquKH+OoIgiLo3R6PR5zY3N9/z3o8DFr/mnHs0IG6QIQiCIOrGtNbeJyLvBC780Dl3ODB2cGEIgiDqprTWPi4iLygWjpxz1xTxgwlFEARRN6O19ikRuaBYeMY5t62IH0wogiCIuhkRZCmybefcGTXQASyw1p4WkUuKrVwY0kf5RrHx7KEIgiCLGwSCLOkDBEEQBNnnHEIQBEEQBPkfAYZ0hnT1zMIJwgnCCcIJwgmy/2+dDOnL+HCCcIJwgnCCcIJwgqjHjztNwzfpe6Pji8K4llp7FV8Uro0wLgGfYvEplrpzmEGYQZhBmEGYQZhB1IcHM8j+yJhB4lpq7VXMIGsjjEvADMIMou4cZhBmEGYQZhBmEGYQ9eHBDMIMcocAf9RkWS9wxeKKxRWLKxZXLK5YXLFWEeBTLD7FWtUjn/p1rlhcsbhiccXiisUVS3148CkWn2LxKdYqbbhiccXiisUViysWV6xVZ8Xev84JwgnCCcIJwgnCCcIJsooA34PwPciqHuF7EJHFP+wc8oO/DxJCKUMMfx8kA9SQlJwgnCAhffKxGIZ0hnSGdIZ0hnSGdPXhcadp+Hex9kbHDBLXUmuvYgZZG2FcAmYQZhB15zCDMIMwgzCDMIMwg6gPD2aQ/ZExg8S11N"
			                                        "qrBjWDTCaTn3jvnwt9qo2NjVNXr179Y2j8kOImk8kvvfffCtmTMeZX0+n02yGxQ4s5ceLEV3d3dy+H7ssYc346nT4fGp87blCCKP/L4BtbW1ufv3z58s3ckHLkt9Y+ISLPBOZ+0jn3bGDsoMJOnTp14MaNG/8Wka3AjZ1xzm0HxmYPG5QgJ0+e/OLNmzf/HvjUv3fO3R8YO7iwyWTysPf+jZCNGWPOTqfTN0NihxhjrX1HRO4L2duBAwe+dOXKlX+ExJaIGZQgiwe21j4uIi8EPPw3nXNvBcQNNsRauxDk4RUbfNM5d3awDxGwMWvtQyLy64DQHzvnfhoQVyxkcILclmTxheF5EbnrkySMMR94718c0n82H/u2jh8/fs/m5ubLIvLAkhwX5/P5D69du/aX2BpDWbf4CN8Yc857f2SPPf1LRJ4b4jsdpCALgOPxeCQiPzLG3CsiXxORxb10ez6fv/hZaJiPNom19rHbkiyec/HjXRG56Jx7aSgNnmIft39DOCf//1PMi5/veu/fE5GfzWaznRQ1UucYrCCpH5R8EIghgCAx1FjTDQEE6eZV86AxBBAkhhpruiGAIN28ah40hgCCxFBjTTcEEKSbV82DxhBAkBhqrOmGAIJ086p50BgCCBJDjTXdEECQbl41DxpDAEFiqLGmGwII0s2r5kFjCCBIDDXWdEMAQbp51TxoDAEEiaHGmm4I/Bct260jxu1OmwAAAABJRU5ErkJggg==\"/></p></body></html>\n"
			                                        "                ", None))
		self.label_setting.setText(
			QCoreApplication.translate("Form_Main", u"<html><head/><body><p><img width=\"30\" height=\"30\"\n"
			                                        "                    src=\"data:application/octet-stream;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAYAAACtWK6eAAAAAXNSR0IArs4c6QAAIABJREFUeF7tfQ+0XUV1997nvpe8Jgb5BG2hBQJNQ7izzw3poyAFWmhB/liUT7BStPwPSIlLtApCKfZDqdIWCcofFUEJf/QDURCEaoNEEAH7RcI9M5ckpjEiILGJooHweI979rd2OCmP8N67M+eec8+c986s9Vay1t2zZ89vzu/MmZk9eyNUpUKgQmBcBLDCpkKgQmB8BCqCVE9HhcAECFQEqR6PCoGKINUzUCGQDoFqBkmHW1VriiBQEWSKDHTVzXQIVARJh1tVa4ogUBFkigx01c10CFQESYdbVWuKIFARpIuBJqK3MfOAMeZbXajJrSoRfRwRf9Rut+9rtVrDuTU0iRVXBHEY3Hq9vm+tVjuamY8AgH2Sqr+cPn363OXLl//GQVXuokR0MADcv7UhZr4XEe+N4/gHrVbrsdwNmCQNVASZYCAbjcbucRwfAgCHMPNfIOLOY4kz833GmEN9eiaI6BcA8Hvj2LQGAO5DxAfb7faDrVbrSZ9s98mWiiDbjMbg4OAbh4aGjkHEYwBA/qwKM3/aGHO+lXDOQkT0VQA43qGZO5j5joGBgTt8mwkd+pCLaEWQBFal1OEJKd4JADulQRsRG1EURWnqZlWHiN4PANek1Cezzp1CFmPMd1LqmFTVpjRBiKghpIjjWGaMBVmMbBzHO7VarWez0OWqQyl1PCLK7NF1YebHgiDYMrNorZtdKyypgilJkDAMj2JmedMence4IeLboyi6Jw/d4+kkIpk1pE95lLsQ8fO97lMeHXHVOaUIEobhoQkxjnUFKoX8hVrrS1LUc66ilLoDEeXTMO9ye0KUpXk35Iv+KUGQRqNxEDOf"
			                                        "xcx/02Pg5YE6N4qitXm022g09ozj+DoAOCAP/ePplM84RLym2Ww+2Mt2i2hrUhOk0WjslxDjpCLATdp8FhGXxHF8gzGmlYUdSql6EAQnMfOJE2zlZtHUhDoQ8YaEKI/m3lhBDUxKgsj5RbvdPh8RFxaE61jNjgDAkiAIbkj75pWZMI5jIbsQo9+XvjHztbVa7VPNZvOnvtiUlR2TjiBEdBoAXAQAu2YFUg56ZHfogVqt9vN2u/2zdru9duXKlRtHt6OUelNfX99u7XZ7NjPvhoh/7nIuk4PNnVTKYePFWmv55Js0ZdIQRL7H2+32RYh4QklH59cAIA8ZJ+R+Uxn7wcy31Gq1i5vN5qoy2r+tzZOCIER0VjJrjOda0fVYyfd2HMdXIeJbAeCzXSssRsEFiPjdOI7PQMQzcjRBzoFkNkl7YJmjaW6qS02QMAzDOI5l1jjOrdt20oho4ji+kZmvarVaz2+tFYbhkczc03MOO4vHl2LmRcaYq7ZKDA4OzhgeHn4fMwtRBrvVP1Z9Zv56EAQXF+1d0E3fSksQIvpgMmvk8SlyGzPfaIy5azxwt/WW7WYQ8q7LzCcZY5ZM1BfZAs9pVvlVMptckXc/89BfRoIgEV2d9amxzBbMLMS42Rgj3q4dS71e3y8IgpsAYE5H4QIEEPEZZj5Ta323TfNEtEtyViQuK5m43oxqd4nW+hQAiG1s8UWmVARJtm9lHXBkVgAi4r8DwPVRFN2WRqf4c4knb5Y2pbFj2zpy/yMIgn+Momh5Gn1KqWODIDg9ufuSRsXr6oh/V61WO73ZbP44E4U9UFIagiSfNPcCwEBGuDwex/HiVqv1lSz0hWF4AjN/AABkEV9keQQRPxdF0S1ZGFGv108OguAcAJifhT4AkPOgs8qyHVwKgoRheAozX5/RAK1HxMWbNm1avG7duqGMdP6PGqXU2Yi4CADmZa27g76VzHzl6IV4Vu3Pnj17YNasWecwsxDld7PQm9gqLxSvi/cESXH5ZyLArwiC4Iq8T3z32"
			                                        "GOPN86YMUNIcnLe6xNmXi2uLJs3b75y7dq1uV77TW5YyuaI/GVRfqC1PigLRXnp8JogRCSny1nsUt0qs0YURQ/nBeR4epMtYVkzyV8mi/lkQ+EOAFiqtV5WQJ/2T2aTv86g7ee11rMy0JOLCm8JQkRyotxteQAAFmutv9mtoizqS9CHIAjeAQASUGGHUX/BOPplx0deElv//iO57fd4FvZ0q4OI/jcAyGfXn3WrS2vt5bPopVFZkIOZP2aMubTbgetF/b333nv7l19+eYc4joU0EATBxr6+vo0rVqx4rhftd9tGGIbnyU5et3p8JIl3BMmAHOuZ+WxjzO3dDlhV3x4BIpLPrSsB4M32tV4v6RtJvCJIBuR4KI7jRa1Wa0U3g1TVTYdAGIaDib/afuk0vFLLJ5J4Q5AMyLFkZGRk0apVqzZ1MzhV3e4QmDNnznYDAwNfcAw79LpGfSGJFwTplhyIeFEURZ/obmir2lkiQERyH/+CbnT6QJLCCUJENyQ35NJgOcTMpxpjMgl1k8aAqs74CCilTkJEmU2mp8TpJq3136asm0m1wglSr9dVEATatTfMLM6Fp7ZarR+51q3ke4dAGIZyZiK3DPdybZWZ9zXG/KdrvSzlCyeIdIaIZMfpXbYdY+Y7AUBmDnGlrornCMybN2+HWq12nUtoIkT8XhRFf1l017wgSBL2U7xqrYqEnYmiqKxXa636ONmEiOhWAHi3Q7/eo7WWOoUWLwgiCIRheJ9EULdEY43W+o8sZSsxDxAgIokNtrulKY9orfe3lM1VzBuCENGpAGAdEcOHHY5cR2aSKXfZqWTmhcaYL/kAgU8EaQCAtY8RIu6T9jKQD8BPJRuShfoPbftcq9X2fPzxx1fbyucp5w1BkgMma3dtRDwziqIv5glOpTsbBIhI7n3YRoL5ldZ6i0+aD8UbgggYRPQUAPy+DTDM/EVjzJk2spVMsQgQkXwuSUA/m/KQ1vpAG8FeyHhFEKWUXBe18uPxZRuwF4NU9jYcN2Cu01qf7k"
			                                        "ufvSIIEf1fALC9hHO31jqX/B6+DM5ksYOIJHzSX1n25yNa68ssZXMX84ogSimJDnKeZa9v01rbkslSZSWWBwIuZyBFJB+aqM9eEYSIFtved5ZQoFEUyZ3vqniOQBiGX5HgdTZmSlwuY8zXbGR7IeMVQcIwvMUhyc3ntdYSk7cqniPgkh4OEc+Poqjr24lZQeIVQZRSSxHRyv+GmS83xnw4KyAqPfkhoJT6DCJ+yLIFr158XhGEiCSFMlkCeYnW+kJL2UqsQASI6JMA8A82JkikyyiKMoucadNmmdYg6wHgLZadOr0s0fks+zNpxRwD/63UWju7xucFnm8ziHWoH2ZWWeX8ywvcSu8rCMyfP39uu922Tagz1N/fv+tjjz323z7g5w1BiEhyfNsmXFmvtc4tWY4PAzPZbAjD8Glm3tmyXxK79/OWsrmK+UQQyZS6r2Vv79JaSwC2qpQEASKSrdv32JjLzPcZYw61kc1bxguCENGfAsBDDp29UGstQQGqUhIEiOjvAeDfHMw9QGtt7QHsoNdJ1AuCKKWuRMSzbS1HxMOiKFpqK1/JFY+Aa0YuZv6MMUZIVWgpnCD1ev0NQRCstPXiBYD1Q0NDc9esWfPbQpGrGndCYM8995zV39//E4f0CU/GcaxG54Z0ajAj4cIJQkQfBYB/cejPZVrrjzjIV6KeIEBE8onlMisU/ildKEGISDw8x02UOda4xnG8oAot6skT72hGvV7fOwiCx1yqIeL7oyiS2FqFlMIIopSag4gy5VoXSVJvjHmvdYVK0DsElFI3I6JTRJogCPZvNpuPFNGZwghCRJJs3imdFyIeFUWR5CmsSkkRSJlj/jda6+2L6HIhBCEiiYb4J44dvl9rbRsWyFF1Jd5LBIjoewBwiGObhbig9JQgRCQzhqQmSHMKfprWOqtEno5jk6+45DScOXPmDu12e0dpqVarbXjhhRc25p1zMN9eja/dNcTTKE1rNm/evE8vcekZQZRSpyPitWkGZbJcjgrDcI84jt+JiOI"
			                                        "FIGSQ6B3yb/84uEjK5A1JCrYNzHwbM9/darWeTIOjT3VcLlGNYfchvcrN2BOChGF4KTOfm3KAlg8PDx+xevVqeVBKV5K8hEci4pHMbBWQwqKTkrjzbmZeaoyxjiVmobdnInPnzt1x2rRpEm52ME2jzPxhY8zlaeq61MmVIER0GCKezMxOuxajOvASABzRq7eFC3CdZInoNERcmCEpxmySmR+VmbmMrv/J6bqQJG16hBuTOM25bdxkTpB6vb5AMrki4rvFJb3TgzTR74j4gSiKJO9daUoYhicw898BwAE9NvohRLw6iqJbetxuV82FYbiImT/XlRKANQAgJPla1v5bqQkyODg4Y2RkZJc4jncFgF3kLwtSjALqC1prcYEvRUlSIgsxivZCFR+1q31JfW0zeEQkru1ZBQEUstyEiGviOF7Xbrefnjlz5tPLly+X9ZxzcSZI4i5wFADsBgAznFu0q1CakD7iYzRt2rTrmfk4u671TOobw8PDZ5Zl7eYSGigFgpJHZh0zf9YYIxnNrIszQRyj5FkbMkqwNOTYa6+9duvr6xNy+Ho+02TmE8uykM+ZJPKIOUdtdCKIbFMCwGpmrqV58i3qlIYciV/R9wFgO4t+FSnyIiIeF0XRPUUaYdt2ziT5idZ6HgDEtvY4EUQpdSwift1WuaNcacjhmhHLEYdcxJn5DGNMqnOoXAyaQGmeJHF1V3IiSAp3ZVtsS0MOIvo4APyTbcc8k/snrfX/8cymMc3JiySIuDiKItsYXeBEEKWURsSutm63QeP/JQbfXIZBU0otRMS8cpJsRMQtJ+TMLDuDueTIYOYjjDHfKQPeYRi+l5nPAYB9MrRXa61DW33WBGk0Gn8Qx/HPbRVPJMfMzwgxdtxxx8uXLVv2chY689YRhuFRzPztjNqRPCjLJFsvIpogCJ5sNpsvjNbdaDRmJlvo8s18ODMfjoizs2i/THdqDj744L4NGzZ8SIiCiLZRUTrBtKvW2upZtiYIEUlEiq6DCgsx2u325WXyJ1JK"
			                                        "zUfEhwHgdzohP97vzLwBEa9k5geMMfen0aOUOgARD2XmRYi4xbExZfltu91uPPHEEz9LWb/n1er1+q61Wm0LUTJo/HittaTa6FisCaKU+hQifqyjxjEEJIwLIt7JzPcaY+QgpzQl8Rm6DwAkh2Ka8hIzX1Wr1a5sNps/TaNg2zqNRmP3drstJJFAF6ncNCQB0fDw8DGrVq3alIVNvdJBRBJ18V3MLBtGC9K0y8yfNsacb1PXhSD3iMOdjdJE5pcAcAUz31o2UozuIxHdLgPi0O/RokuS6By5OBTKzBYEwXkOEfFf0w3ZkYyiyCV3eUoY8qkWhuFgHMdnIKLkibG+UJW8qOWwu2NxIcjTtt+AzHyeMcYlEENHQ4sQSNxHvpGmbfkMMsZclaaua50udxffVSa3lPGwUUqdh4hWaRNkDWyMscqFaUWQBQsWvHlkZERmBNtyrNY61YNl20Av5IjoP9L4VsVxvF+r1ZJbkz0rYRiKc+itKRpcqrU+LEU9r6o0Go3j4ji+zdao/v7+t9jE/7UiSBiGsjCUh8W2zNdaN22FfZRLvHKdt5+11laY5tVnIrIOAL7VBkR8b9m8gLfFb/78+Qva7faPbXG1DT5oNZhEJHGo/tWmcURsT5s2bbvly5dvtpH3VYaIfuDqsi7fwlEUWb/F8uh7ckFL4hy7FK9SL7sYvlU22RaXYIKBZf2Paq07hkK1JYi4KNim5i3kcr0lKFZictkJACS3t0vxJqCdUups2VJ2MV7Gt4yXrkb3kYhWA8AfWfb7S1rrhZ1kbQki+/YHd1KW/F76yOsu+dqlz8mttrS3Ji1hdRMjInHrPtG2FiI+GkXRW23lfZQLw/Be8RSwtG2Z1rpjZBVbgsjJr9Wq35egw5YgvU4sORSUyCu2Rc459vPNpTzph3xqWZ+TFLG5YAuyjRwRya6hXFqzKU9rrf+gk2BHguy///6/s2nTJpf1hDfJTzp1fqzfXcP0+/xCUEpdhoguiU5L48w4zth9EAAklbhVmTVr1oyHH"
			                                        "374xYmEOxKEiOQE2fqgKwiCQ5vNppw8l7IQkfXnpLiP1Gq1fbM6Ic8asOTE/Ue2bill/8xSSh2BiC4BHDruttoQRE6R5TTZqrTb7dll8vEZ3Snx9wmCwMU/yfs3rqt7PiL+YRRFa60G2zMheSHEcexie8fzuo4EUUqdi4iXWmIxpLVO7dBn2UZuYkqpv0NE69NvZj7QGOOSGSs328dTrJQ6RPyubBvuVbwpW3tc5YhoyHbdZePx0ZEgRPTPAGDl2AUAkdY6rVOfKxaZyzt+Xq0zxuyeuRE5KCQice3uuCBNmrba3cnBzExUElEEAGSp7FNa6wu6WoOEYXi5g4vxVAK3NGGJiOhGAHif5UPjdKHIUmfPxFxecja3C21mEJeYRWUnyDMAsJPlaJbGyU8pdRwi2p7w/0JrndXFJEsosxNzIQgAdHzJdSSIY5DhshNkeIJA0tuOYl1r/UR2Q5ufpuQORcuyhRGt9TRLWe/EXAhiExS9I0GISG5eib+9TSktQSQFwYwZM56z6aTIBEHwhm2vydrW7bVc4qf0vG27mzdv3r6XKQZs7bKRcyEIANyqtZ4wd7sNQb4FAEfbGCf3rG2O7y119VRMYn4x839ZNrpRa93NlVfLZrITIyKJjm8VCKLMW72OBOnoFmVDEJc7EaUliIsXLCI+FkXRH2f3+OavKQzDHzOz1RXVMrucOBKk410YG4JIiJi3WQ5hRRBLoHotVhFkTMS7J0gYhpLVyDYwc2kJUn1ivfoAVZ9Yo7Do9CYjIskLeEonueT30hKkWqS/OsLVIt2NIOIdKV6SNqW0BJHOEVG1zQtQbfOOetI7rkHCMPwEM19ow44y72IlBKkOCgGqg0IXghDRRwHANoRP2WcQFz+ejqewli+V3MUqV5OxIc7K1UTSoF1jOYpNrfV8S1nvxFy2CJm5clb0bgS3fCa7vOQycVaUCNs3WWLxotY6r7RsliakF6vc3bdElu9JeuX0ozRxzZ67uyuljkZEOU23KtWFKSuYeiZUXZiaEO"
			                                        "ruL0wluayto5FLvr600ct79tRM0JDjZ1Z15daHQUtsKOTKbaPReEscx+ttcWDmhcYY15hStupzl6uCNpQjA9VYDwIR9T5oQ7L96eLo9i9RFJ2X+5OcUwNV2J/exhTOchgLCfuTEORBADjQsjPf0FofaynrpVgVOM7LYeloVGGB45RSX0DEMzpa+IpAqbd6kxdCFXrUcrB9Eiss9KhSSvLDXW4Jxot9fX07r1ixwvrykaXenopVwat7CnfXjRUavNo1L3gQBIPNZtM6FH3X6OSgoEp/kAOoOaosOv3BLgCwJUWxTfEhDYCNnZ1kqgQ6nRDy5/dCE+gk3+WS7PENNpAwsyT7vNYY8ysbeV9lqhRsvo7M6+0qNAVbQhBJKfYnDpA9gYiShOb7cRxLdttSkqVK4ukw4j0W9S2JZzdpoJ9BxPslsHAURc5pzXqM+2uaq9JAF4n+69v2Ng10vV4/MAgCOQ/ptnwbES+JoujhbhX1qn5yeCj2po47LJHgJesTMz+Q1hVHKXUAIkq+SMmR3k1Uld+22+1GmYKMS2DxWq32IYconxM9HsdrrSWcVcfS8cLUVg2Dg4P9L7300n8DwBs7au0s8DIAfHLHHXe8ZNmyZfJ/70sYhkcx87czMlQSEi1j5jsR0QRB8OS2MbaSbctdAWAeABzOzIcj4uws2o/jeEGr1XJJEpRFs6l0HHzwwX0bNmzYQgzbNOSdGgqCYA/blBXWBJFGlVI3I2KWqcbkrXyJ1jqrB68TNl39rpRaiIhf7ErJ+JU3IuKWnUJmFmJYxbBytUVSlBljJFKN9yUMQ7lqcQ4A7JOhsWu11n9oq8+VIHk9IB0vrth2KG85V/fxvO1x1O99PpOt/SEiyfn+bsf+dRRn5luMMe/tKJgIOBGkXq/vHQTBY7bKHeWWaK1PcqxTiLjrwWkhRm7TKDOfYYyRbMXel7zIIR1HxPdHUfQFWxCcCCJKiUgSxvypbQMucsx8nzHmUJc6RckmL4vvA8B2Rdlg2e6LiHhcFEX3WMo"
			                                        "XKpYnOQAgZubQGGMbyBucCeKYLyQN2KXJs77XXnvt1tfXd71cEkvT0R7UaTLzib5l4B2v3zmTQ5r9odb6ABfc0xDkBGaWSCeyo7K9S2MOspu01r6/mbd0Z88995w1bdo0IYlt9EkHGLoS/cbw8PCZq1evlrs83pecySGR7dcx83eNMX/vAoYzQbYql23foaGh3QBAEl/uJjsviPhuZlYuBkwgu0JrbRVsOaP2ulKTuKVIju6iPxGXAsDVWutvdtWhHlYmIpckTZ0sWwMAEmRkLSL+jJmffu6555556qmnJkz3PJ7S1AQZT2G9Xl8QBME7MiLLB7XWn+2EiE+/J17AQhSnqTyDPjyEiFdHUXRLBrp6piIMw0XM/LkuGxRSSPrnr2mtf9ilrtdUz5wgo7UT0WGIeDIzpz47KUMm2bEGhIhOQ8SFzLxflgO2rS5mfhQRr9VaX5dnO3noTgKC/LttVtoxbLgREb8aRZFLbnSnruRKkK2WhGF4KTOf62TZq8IyVe4TRdGvU9YvtFqSd+RIRDwyQ7IsA4C7mXlpWRbg2w5C4uMm5BhMM0C9it/VE4IIAEqp0+VNlxKMrxhjbCPMp2miJ3UkxUIcx+9ExHcAgPhSyWm5/Ns/jgEjACCL7I3yLzNLKoq7W62W9d2cnnQsRSOOuS+3beEQrbW8JHIvPSOI9ISIfhcAxAfo91L07DSttaRimHRFUi/MnDlzh3a7vcUBsVarbXjhhRc2ljVPYKcBIqJTASDNJ+GazZs379NLXHpKkK3AEZHr3RKper/W2tfzhk7PRPX7KASI6HsAcIgjKIWcjxVCkGQ2eRYAZEaxLoh4VJ4LMmtDKsHUCIRhKGsx11P932it8zpzm7AvhRFEKTUHEX/igrSro5mL7kq2Nwik8QgPgmD/ZrP5SG8sfG0rhREkmUX+CgDucul4me4yuPRrKsimcXZ1dS7MGsdCCZKQxCVBj1S5TGv9kayBqPTljwAR/RsAuLh6XKi1viR/y8ZvoXCC1Ov1NwRBYMRl"
			                                        "xRKI9UNDQ3PXrFnzW0v5SswDBMRnrb+/Xz6prdadkqBoYGBALV++fHOR5hdOEOm8UuoyRPywLRCIeFgUReJzVJWSIJAijcanjTHnF909LwhCRHK/RO6Z2JbCp15bQyu5VxBwTSvhy1rTC4Iks8hSRPxLywfqLq21nEZXpSQIENHXAOA9luZ6kwzWG4IQkUuy0PVa6zSn8ZbjU4lljUAYhk8z8842euM4PqXVan3FRjZvGW8IsmDBgjePjIyIj9GATafl3onL1UkbnZVMPgjMnz9/brvdXmWrXWvtzXPpjSHJZ9YqRJxrCeTpZXTxtuzbpBILw/AUZrb1o/ul1tpqp6sXIHlFEMdo6qUJYdOLgfS5DSL6JAD8g6WNWmsdWsrmLuYbQcTDUzw9bUpFEBuUPJBRSn0GET9kY4pvkW28IohS6h8R8WIbIAGgIoglUEWLEdE1ACCbMB1LckMw9Q3Ujg04CvhGkBMQ0Tb6e0UQx8EuStzxctQVWmsJN+pF8YogRPR2uUpqiUxFEEugihZzCenDzF6coG/FzCuChGF4ngBkOaAVQSyBKlqMiMRjWzy3O5bqE2sCiIjoRgB4X0cUXxGoCGIJVNFiYRje5xB98iGt9YFF2+zlDEJEjwLAvjbgIOKpURR92Ua2kikWASL6EgBI7nmb8pTWWpLGelG8+sQiIslj+L9skCnylpmNfZXMqwgQ0QcAwDoA4MjIyHarVq2SpLGFF28IEobhPGZ+whaR6dOnb798+fLf2MpXcsUhEIbh/sxsHfEwCIKw2Wzq4ix+tWVvCOIYCqawS/w+DFoZbSAitrWbmRcaY+SzrPDiDUEcF3KPaK33Lxy9ygBrBIhoLQDsblnBm/H1giApMjZ9WWtt65JiOSaVWJ4IuJyFJHa8R2stadgKLV4QhIhuB4B32SIh2WHFZ8sYI4v6qniOwLx583ao1WrXIeI7bU1FxO9FUWR7gc5WrbNc4QSp1+sqCALnBRkzG2Y+tdVqSZTGqniKQLJAFyfUvVxNZOZ9j"
			                                        "TH/6VovS/nCCUJENwDAiSk7NSQkMcZ8NWX9qlqOCCilTkJESZg5PWUzN2mt/zZl3UyqFU4Q6YXLDsdYvUbEi6Io+kQmiFRKMkGAiCSe1QXdKPPhZqEXBMmCJACwZGRkZJEvB0zdPBhlrjtnzpztBgYGZNY4vpt++EAOsd8bgmREkofiOF7UarUkxUJVeoxAGIaDcRxfhYhdZdXyhRzeESQjkqxn5rONMbIzVpUeIUBEfw0AVwLAm7tp0idyeEmQjEgCzPwxY8yl3QxWr+ruvffe27/88ss7xHEsGacgCIKNfX19G1esWPFcr2zoph3HawrjNuUbObwlSFYkAYAHAGCxLymRk3yFEvDu4CT9mhBC/oJxnpo4Sb8mKdjk7x5mvtUYI1ldCy9J6mu5/fdn3RrjIzm8JkhCEnko3tQt+ABwKyIujqLo4Qx0OalIEsYcCQDyN8ep8jjCzPwgIkq+wnuLIEtytiHEkM+qbsvzWutZ3SrJq75Xi/SxOklEcsbR1Y7IKL1XBEFwRbPZ/GlegIpeyTk4Y8aMRQBwclakGM9eIQkAfNMYkypBqgsOjUZj9ziOPwgA8pdF+YHW+qAsFOWlw3uCSMcdA491wmq9zCabNm1avG7duqFOwq6/K6XORkQhxzzXul3Ky+x4tdb6pi71vK767NmzB2bNmnUOM8uskUlQN2a+0hgj90S8LqUgiCCYhM+Xt6VVaFIL1B+P43hxVjFgwzA8gZllwN9q0XZuIuLDFMfx1Vnt4tXr9ZODIBBizM/IaEltfVZZomKWhiAyODLFt9tt2WeX7/lMCiJKMvvroyi6LY1CImpIoIksbUpjxxh1vo2IH4+iaHkafUqpY4MgOJ2Zj0iFNVj+AAAEHElEQVRTf6w6zPxYrVY7vdls/jgrnXnrKRVBEjCQiK62DURmCyAiivOjLHxvtl341uv1/YIgkE+aTBbftrbayiHiM8x8ptbaKpQSEe3CzH8jaz5EXGDbjqXcEq31KQAgO3OlKWUkyBZwiUgWihdltM"
			                                        "u17YAJUW40xoybYNQ1Y1KRTwQzn2SMWTKeDdIXIQYinpGDnXIl4WKt9RU56M5dZWkJIsiEYRjGcXwRIh6XB1Iyq8RxfCMzX9VqtZ7f2kbKXN95mGitk5kXGWOu2lphcHBwxvDw8PuYWUgxaK3IQZCZvx4EwcVRFEUO1bwSLTVBtiJJRGcls0luSXUQ8YbEz0gW4dYROrwabYALEPG7cRyfkdNssbW7zyazhsTkLXWZFASREWg0Gnu2222ZTbwJfOz4ZPwaACSBkAQ3kIy/WRyQOprQvTgz31Kr1S5uNpvWCXO6bzU/DZOGIKNmEwlQJmsT27TS+aE7vuY7mPmBWq3283a7/bN2u7125cqV4jXwP0Up9aa+vr7d2u32bGbeDRH/HACOKcJYyzaF3LLWkNuDk6ZMOoIks4lsB5+PiAs9GinZ/18SBMENzWbzwTR2NRqNg+I4Pim5gdmfRkcedZj52lqt9qm8PRTysL2TzklJkK2dbjQa+zHzWbKL0wmIHH9/FhGXxHF8Q1Y5FZVS9SAITmJmuaqc27qrEyayLkPEa5rNpoSMnZRlUhNkFFEOSogie/y9LLcj4rlRFElMqMzLvHnz5vb391/jEBg6ExskAntCjFQzYSZG9EjJlCDIVizDMDyUmSXT0bE9wPdCrbXcy869OCao6cYeIfznoyha2o2SMtWdUgQZRZSjEqIcncdgIeLboyi6Jw/d4+kkoo8AwL/m1OZdCTF62qec+uKkdkoSZCtC4keFiMfEcXxMVq4VcRzv1Gq15Byg50W2uuM4XplFw+I3FQSB7LbdobVuZqGzjDqmNEFGD1gS/lS2USX6305pBhMRG0WfGs+bN292X19f2vsuvwCAO4UUxpjvpMFgstWpCLLNiA4ODr5xaGhIZhQhi/W5g0+59RIXdZfkQltmioGBgTuqlBKvfSAqgkzwyktu0B0CAIfIThEi7jyWuG+5vcVGpdSXEVFuNI5V/kvc/OM4foiZH2q1WnLIV5UxEKgI4vBYSNCFWq12dHJ"
			                                        "HYp+k6i+nT58+17c3b6PRmNlutzUizk7s/K44DyKiXHO1TlTkAM+kFK0I0sWwEtHbmHnAGPOtLtTkVjUMw6MA4PkoiiS6S1VSIFARJAVoVZWpg0BFkKkz1lVPUyBQESQFaFWVqYNARZCpM9ZVT1MgUBEkBWhVlamDQEWQqTPWVU9TIFARJAVoVZWpg0BFkKkz1lVPUyBQESQFaFWVqYNARZCpM9ZVT1Mg8P8BcBMwqk695SoAAAAASUVORK5CYII=\"/></p></body></html>\n"
			                                        "                ", None))
		self.groupBox_quick_box.setTitle("")
		self.label_music_img_box.setText(
			QCoreApplication.translate("Form_Main", u"<html><head/><body><p><img width=\"70\" height=\"70\"\n"
			                                        "                    src=\"https://y.qq.com/music/photo_new/T002R300x300M000003jpkCG0OOSea_1.jpg?max_age=2592000\"/></p></body></html>",
			                           None))
		self.label_music_name_box.setText(QCoreApplication.translate("Form_Main",
		                                                             u"<html><head/><body><p><span style=\" font-size:11pt; font-weight:600;\">\u30dd\u30b1\u30c3\u30c8\u3092\u3075\u304f\u3089\u307e\u305b\u3066</span></p></body></html>",
		                                                             None))
		self.label_next_box.setText(
			QCoreApplication.translate("Form_Main", u"<html><head/><body><p><img width=\"25\" height=\"25\"\n"
			                                        "                    src=\"data:application/octet-stream;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAYAAACtWK6eAAAAAXNSR0IArs4c6QAAERVJREFUeF7tnXusZVV9x39r3zvMTVDRSl8+sGkmzOTstU/GDOGNHUpBwWhbWm2xPkDQkWLv4INYQ3hKiK0i0laKT9pYX4BIULGWRMeURmt7ncvZv3WGmYx2YkuIdmooTs1cvHevZpFzYa4zc+8+67fOPmuf9d3JhD/u+v32+n1++8M56+yXImwgAAJHJaDABgRA4OgEIAiODhBYhQAEweEBAhAExwAI+BHAJ4gfN0QlQgCCJNJolOlHAIL4cUNUIgQgSCKNRpl+BCCIHzdEJUIAgiTSaJTpRwCC+HFDVCIEIEgijUaZfgQgiB83RCVCAIIk0miU6UcAgvhxQ1QiBCBIIo1GmX4EIIgfN0QlQgCCJNJolOlHAIL4cUNUIgQgSCKNRpl+BCCIHzdEJUIAgiTSaJTpRwCC+HFDVCIEIEgijUaZfgQgiB83RCVCAIIk0miU6UcAgvhxQ1QiBCBIIo1GmX4EIIgfN0QlQgCCJNJolOlHAIL4cUNUIgQgSCKNRpl+BCCIHzdEJUIAgiTSaJTpRwCC+HFDVCIEWiOI1vrNRPR7RPQq1xtr7Z4sy+4ry/I9ifQKZY6BQCsEKYris9bai47C594sy7b3er3/GgM/7HLCCUQviNb6OiK6fo0+lNba7caYb054v1BewwSiF6QoCrbW5jW4LCiltpdl+dEaYzEEBGoRiFqQTZs2/cb09PR/1KrkmUG3MPO7h4zBcBA4IoGoBdFabyWiob82KaXun5qa2j4/P78PfQcBCYGJFGQA5BEi2s7M/yQBhNi0CUyyIK6zS4PF+0fSbvNoq9dan0dEXSI6Qym1p6qq7xpjvjjavTaT"
			                                        "fdIFWaZ4GzNf2QzSdPaS5/kGpZT7lfH1R6h6h7X2VmPM/W0mkoog7sTi14ho1hizt80Ni2nueZ4/oJQ6f5U5/YSITmbm78c072HmkowgAyh7Bz8FPzAMJIw9nEDN81Mu8EvMfGFbGaYmyHKfrmTm29ratBjmrbX+JBG5y3/W2p5g5uPWGhTr31MVxPXjdma+ItbGxD4vrfXXicgtztfclFInlWU5t+bACAekLIhrx4NZlm3r9XrDnoyMsJXNTklr7c5PufNUdbazmXlHnYGxjUldEFJK7XPrkl6v1+pfW5o+sCBI08SPsD/fM+meU7+KmT/oGZtcGASJoOVDCuJ+mbpAMm1r7ceMMdskOVKJhSARdHpIQdwl8ccS0VXCqe+oqupN/X7/h8I8Ex0OQSJo77CCMPMNnU7n4izL7hRO/9HBJSoTcbmEkMURwyHIKKgOmdNHELeLTqdzcpZldxHRS4bc5YrhSqn3lmX5fkmOSY2FIBF01lcQN/Vut3vs0tLS3WtcClGnyjuZuc4JsTq5JmYMBImglRJBlqevtf4AEUlvoHooy7KLcN/7MwcFBJkQQVwZRVFcYq39lLCkH1lr326MuUeYZyLCIUgEbQzxCbJcxmBdcjcRnSApzVp7rTHmfZIckxALQSLoYkhBBov3Zyml7gqwLvk0M78xAkRjmwIEGRv6Fd9zh7kn/Xr3M2+daWut3Rnzd9UZu8qY7ywtLV24a9eux4R5WhkOQSJoW+hPkENLGjyp0V2yLdncDUGXMfOXJEnaGAtBIujaKAVx5XW73VOqqnLrkhdLyrXW3miMcbeeJrNBkAhaPWpBXIkbN2589jHHHHOXtfYVkpKVUp8ry/J1khxtioUgEXSrCUGWy8zz/Bal1DuFZc9lWXZBr9f7sTBP9OEQJIIWNSmIK1drfSkRfUJY+hPW2je0/WkeazGAIGsRauDvTQsyWJecWlWVu45LtC4hopuZ+eoGMI1lFxBkLNhX7nQcgrgZbNiw4TkzMzNOkpdLMFhr7zHGv"
			                                        "EaSI9ZYCBJBZ8YlyCHrkg8ppd4hRPHw4uLiOY888sj/CPNEFQ5BImjHuAUJuC75GRG9lpm/GgHWIFOAIEEwypLEIIiroCiK06y17ivXiyQVKaVuKsvyGkmOWGIhSASdiEUQh2LLli3HLSwsOElqPQtqFXz3MfPvR4BXNAUIIsIXJjgmQZYrKoriVmut6EHYSikzNTV15vz8/ONhSDWfBYI0z/ywPcYoiJtknueXKaU+LkT0c2vtq40x/yjMM5ZwCDIW7Ct3Gqsgg8X76UTkvnK9UIjqBmZe6yWlwl2ED4cg4ZkOnTFmQVwxmzdvfu7i4qKT5Nyhi1sZ8BVmfur9723ZIEgEnYpdkGVEWusPu9e9SZBZa/csLi6etHv37p9K8jQVC0GaIr3KftoiyGBd8hal1MeE2Kw7e8/MDwrzjDwcgowc8do7aJMgA0nOcM/jsta+YO3qjj5CKXVtWZZR3/cOQSQdDhTbNkFc2UVRPG9wUvF3hBgeYOZXCnOMLByCjAxt/cRtFCTkuoSIfrB+/fpibm7OXaoS1QZBImhHmwUZfJq81Vr7USlKa+05xphvSPOEjIcgIWl65mq7IK7sTqdz5uA5wb/uiWE57GpmvlmYI1g4BAmG0j/RJAgyWLz/kjupqJQ6x5/GU5FfZuZXC3MECYcgQTDKkkyKIIesS9ybdWdlVOiHBw8ePHHv3r0LwjyicAgiwhcmeNIEGaxLtllr75ASUkptLcvyW9I8vvEQxJdcwLhJFGSwLjlrsC75NQkupdSfl2X5F5IcvrEQxJdcwLhJFcQh2rRp0/OnpqbcuuS3hcjGcn8JBBF2LUT4JAtyyLrkr4joz4S8Hjv++ONP2LFjx6IwT+1wCFIb1egGpiCIo6e1fhsR/a2UZFVVZ/X7/YekeerEQ5A6lEY8JhVBBov3lw0uUflVIdZG3vcOQYRdChGekiDL65Lp6Wn3MO2zhfy+yMx/KMyxajgEGSXdmrlTE2QZS57nf62UentNTEcb9igzu6dDukvog28QJD"
			                                        "jS4ROmKshgXXI5Ed0+PLWVEUqp08uy/LY0zy/GQ5DQRD3ypSzIYF3yW4N1ya944Hs6xD21vizLWyU5IEhIeoFypS6Iw3jiiSce795fIl2XhL4iGJ8ggQ5ySRoI8gy9oij+xlp7hYDn/izLzu71eizI8XQoBAlBUZgDgqwEmOf5nyqlPuKLNeRXLQji24WAcRDkcJgDJu4r1y8Pizrka+IgyLD0RzAegoQVxFr7d8aYS0K0CoKEoCjMAUHCfsUiosuZWXypvZsVBBEe3CHCIUjQRfqBqqpe1u/3dwbqzTeJaGvNXGcz846aY6MapqKazS9MBoKE+5lXKbWtLEvpg+3wK1ZMwqQuSFEUQU4UWmvfaYzBiUKPgxufIB7QmgjRWge51KSqqlP7/f6/hp4z1iChiXrkS/UTJMTFitbafcaY38TFih4H3iEh+ASR8QsaHeqyEiL6DDO/PujkDl8fYpE+SsB1cqf0CVIURZAbptzlKMYY8VXAa/UHX7HWItTA31MRJOAtty/t9/vzDbQG50GagLzWPlIQRGsd4qENu5k5J6KltZiG+js+QUKRFOSZZEHcY3/WrVvn3iUifezPncz8ZgFmr1AI4oUtbNCkCtLtds+qqspdcCh6cBwRXcbMnwxLvV42CFKP00hHTaIgRVEEefSoe3A8M+8aaQNWSQ5BxkX+kP1OmiCB1hu99evXnzQ3N/fzcbYIgoyT/mDfkyJInuehXn9wBzO7M+xj3yDI2Fvw1CXV7mpRd0KqznY9M99QZ2CTYwK+QOeNzPzpJue+2r4gSASdaLsgRVEEeQVbVVW63++bCFry9BQgSATdaLMgWusQL8v5t6qqzuz3+09G0I4VU4AgEXSkjYIEfA30bcx8ZQRtOOIUIEgEnWmbIHmen+FejGOtfYEQ3x8xsztPEu0GQSJoTZsEyfP8LUop6R17NsuybqhnV42yhRBklHRr5m6LIFrrDxPR9pplHW3YQwcOHDh33759B4V5GgmHII1gXn0nsQuyefPm5y4uLrq"
			                                        "vQudKcCml/rIsy/dIcjQdC0GaJn6E/cUsiNb6dPfucyJ6oRDVHzDzvcIcjYdDkMaRH77DWAUJtN5wX6VOYeZeBKiHngIEGRpZ+IAYBSmK4lZrrejnV2vtN2ZmZl41Nzf3s/DUmskIQZrhvOpeYhJky5Ytxy0sLLivVOdJ0Fhr32eMuVaSI4ZYCBJBF2IRpCiK0wYvsnmRBEuWZa/p9Xr3SHLEEgtBIuhEDILkeX6ZUurjQhz/W1XV1qbuFxfOtVY4BKmFabSDxi1InucfUkq9Q1KltfZr1trX9vv9A5I8scVCkAg6Mi5BNmzY8JyZmRm33ni5BIO19hpjzE2SHLHGQpAIOjMOQbrd7qlVVbl3lYvWG0QU/fVUkhZDEAm9QLFNC6K1vpSIPiGc/o+zLDu/1+t9T5gn6nAIEkF7mhQkz/Nb3Dv8hGXfd/DgwTft3bv3CWGe6MMhSAQtakKQjRs3Ptu9Ztla+wpJyZO83jgSFwgiOVoCxY5akG63e8pgvfFiyZSttRcZYz4vydG2WAgSQcdGKYjW2j2NUPrQtf8koguZ+d8jwNXoFCBIo7iPvLNRCaK1/iARvUtY4hemp6ffNj8//7gwTyvDIUgEbQstSKfTeZZS6i6l1PmS8pRS15VleaMkR9tjIUgEHQwpSKfTOcXdL05EJ0hKs9b+iTHms5IckxALQSLoYihBiqK4xFr7KWFJ36+q6nX9fv+7wjwTEQ5BImhjCEG01h8goncLy/mMtXbWGPMTYZ6JCYcgEbRSIki32z12aWnpbul6g4huYObrI8AR1RQgSATt8BWk0+mcPFhvvERYxhuY+R+EOSYyHIJE0FYfQTqdzsVZlt0pnH4/y7JLe73ed4R5JjYcgkTQ2mEFIaJjiegqydSVUp9bWFiY3bNnz35JnkmPhSARdHhIQR4gogsk07bW3miMuU6SI5VYCBJBp4cURDrjqN6/IS1m1PEQZNSEa+RvQhCl1E4iuqIsy2/XmBKGDAhAkAgOhQYE+fy6detmd+7c+d8R"
			                                        "lNuqKUCQCNo1SkGUUjeVZXlNBGW2cgpFUbiHUdS6h6aqqpe29YkuKubujEoQa+3Fxpi/j7n22Oemtb6DiLbVmOfjzPy8GuOiHJKaIN8bXDLyL1F2o0WT0lq7X/vWvMJAKXV/WZa/26LSVkw1JUHclbyzzPyjtjYrtnkXRcHW2nyNeZ3AzO7GslZuqQhyMzNf3coORT5prfXXj/K8Yvc/ovPa+vT6ZeyTLsiiUuqtZVlKLz2J/DAd7/QGX7dOIyL37wdKqR1PPvnktbt37/7peGcm3/skCzKfZdlsr9f7ZzkmZEiVwEQKopS6Z3FxcXbXrl2PpdpY1B2GQNSCbN26dXr//v3/R0TH1C3XWvt+Y8x7647HOBBYjUDUgriJa62/QkSvrNFG97Ym9yuV9FE+NXaFIakQaIMgdX5v7ymlZsuy/FYqjUOdzRCIXpDBp8jlRHT7UZDcOzU1Nfvwww8/2gwy7CUlAq0QxDUkz/M/du/rUEq5E1MdInrQScPM7r/YQGAkBFojyEiqR1IQWIMABMEhAgKrEIAgODxAAILgGAABPwL4BPHjhqhECECQRBqNMv0IQBA/bohKhAAESaTRKNOPAATx44aoRAhAkEQajTL9CEAQP26ISoQABEmk0SjTjwAE8eOGqEQIQJBEGo0y/QhAED9uiEqEAARJpNEo048ABPHjhqhECECQRBqNMv0IQBA/bohKhAAESaTRKNOPAATx44aoRAhAkEQajTL9CEAQP26ISoQABEmk0SjTjwAE8eOGqEQIQJBEGo0y/QhAED9uiEqEAARJpNEo048ABPHjhqhECECQRBqNMv0IQBA/bohKhAAESaTRKNOPAATx44aoRAhAkEQajTL9CEAQP26ISoQABEmk0SjTj8D/AxSx4TJqlBrOAAAAAElFTkSuQmCC\"/></p></body></html>\n"
			                                        "                ", None))
		self.label_play_main_2.setText("")


class Ui_QQLogin(object):
	def setupUi(self, QQLogin):
		if not QQLogin.objectName():
			QQLogin.setObjectName(u"QQLogin")
		QQLogin.resize(150, 250)
		self.label_qr_code = QLabel(QQLogin)
		self.label_qr_code.setObjectName(u"label_qr_code")
		self.label_qr_code.setGeometry(QRect(10, 10, 130, 130))
		self.label_qr_code.setOpenExternalLinks(False)
		self.label_state = QLabel(QQLogin)
		self.label_state.setObjectName(u"label_state")
		self.label_state.setGeometry(QRect(10, 150, 131, 41))
		self.label_state.setWordWrap(True)
		self.pushButton_cancel = QPushButton(QQLogin)
		self.pushButton_cancel.setObjectName(u"pushButton_cancel")
		self.pushButton_cancel.setGeometry(QRect(10, 200, 131, 41))

		self.retranslateUi(QQLogin)

		QMetaObject.connectSlotsByName(QQLogin)

	# setupUi

	def retranslateUi(self, QQLogin):
		QQLogin.setWindowTitle(QCoreApplication.translate("QQLogin", u"\u767b\u5f55\u5230QQ\u97f3\u4e50", None))
		self.label_qr_code.setText("")
		self.label_state.setText(
			QCoreApplication.translate("QQLogin", u"\u6b63\u5728\u83b7\u53d6\u4e8c\u7ef4\u7801", None))
		self.pushButton_cancel.setText(QCoreApplication.translate("QQLogin", u"\u53d6\u6d88\u767b\u5f55", None))


class QQ_Login(QMainWindow, Ui_QQLogin):
	def __init__(self, parent=None):
		super(QQ_Login, self).__init__(parent)
		self.setupUi(self)
		self.is_login = False
		self.qr_code_cookie, self.cookie = requests.cookies.RequestsCookieJar(), []
		self.pushButton_cancel.clicked.connect(self.cancel)
		self.get_qr_code()
		threading.Thread(target=self.ref_thr).start()

	def save_cookie(self):
		open('./MCQTSS/cookie.json', 'w+').write(json.dumps(self.cookie))
		self.is_login = True
		self.close()

	def cancel(self):
		self.is_login = True
		self.close()

	def ref_thr(self):
		while True:
			for i in range(100):
				if self.is_login:
					return
				time.sleep(0.01)
			self.get_qr_code_state()

	def get_qr_code(self):
		resp = requests.get(
			'https://ssl.ptlogin2.qq.com/ptqrshow?appid=716027609&e=2&l=M&s=3&d=72&v=4&t=' + random_str(
				16) + '&daid=383&pt_3rd_aid=100497308')
		self.qr_code_cookie = resp.cookies
		img = base64.b64encode(resp.content).decode()
		self.label_qr_code.setText(
			f'<html><head/><body><p><img width="130" height="130"src="data:application/octet-stream;base64,{img}"/></p></body></html>')

	def get_qr_code_state(self):
		ptgrtoken = hash33(self.qr_code_cookie.get('qrsig'))
		resp = requests.get(
			f'https://ssl.ptlogin2.qq.com/ptqrlogin?u1=https://graph.qq.com/oauth2.0/login_jump&ptqrtoken={ptgrtoken}&ptredirect=0&h=1&t=1&g=1&from_ui=1&ptlang=2052&action=0-0-1665850610729&js_ver=22080914&js_type=1&login_sig=39BSKpFMKjQFXfb7aLAnepoBEMBNTILnbEN8-i8LMC*dUz34jtGThedo9e*AVZ9V&pt_uistyle=40&aid=716027609&daid=383&pt_3rd_aid=100497308&has_onekey=1&&o1vId=7b3d31a8005cd8e7c5d501aa25d12365',
			headers={'Connection': 'keep-alive',
			         'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.25 Safari/537.36 Core/1.70.3732.400 QQBrowser/10.5.3819.400',
			         'DNT': '1',
			         'Accept': '*/*',
			         'Referer': 'https://xui.ptlogin2.qq.com/'},
			cookies=self.qr_code_cookie)
		print(resp.text)
		text = resp.text.split(',')[4].replace('\'', '')
		self.label_state.setText(text)
		if text.find('二维码已失效') != -1:
			self.get_qr_code()
		elif text.find('登录成功') != -1:
			self.is_login = True
			url = resp.text.split(',')[2].replace('\'', '')
			self.label_state.setText(
				resp.text.split(',')[5].replace('\'', '').replace(' ', '') + ' 扫码成功,正在登录')
			resp_login = requests.get(url, allow_redirects=False, cookies=resp.cookies)
			cookie = requests.Session()
			cookie.cookies.update(resp.cookies)
			cookie.cookies.update(resp_login.cookies)
			qq = cookie.cookies.get('p_uin').replace('o', '')
			img = requests.get(url=f'http://q1.qlogo.cn/g?b=qq&nk={qq}&s=100')
			self.label_qr_code.setText(
				f'<html><head/><body><p><img width="150" height="150" src="data:application/octet-stream;base64,{base64.b64encode(img.content).decode()}"/></p></body></html>')
			cookie.cookies.update(requests.get(url, cookies=cookie.cookies, allow_redirects=False).cookies)
			resp = requests.post('https://graph.qq.com/oauth2.0/authorize',
			                     data={'response_type': 'code', 'client_id': '100497308',
			                           'redirect_uri': 'https://y.qq.com/portal/wx_redirect.html?login_type=1&surl=https://y.qq.com/',
			                           'scope': 'get_user_info', 'state': 'state', 'switch': '', 'from_ptlogin': '1',
			                           'src': '1', 'update_auth': '1', 'openapi': '1010',
			                           'g_tk': bkn(cookie.cookies.get('p_skey')),
			                           'auth_time': int(time.time() * 1000),
			                           'ui': 'D3994CFA-AFD9-45FF-93F8-F0B62E52E365'},
			                     cookies=cookie.cookies, allow_redirects=False)
			resp = requests.post('https://u.y.qq.com/cgi-bin/musicu.fcg',
			                     json={"comm": {"g_tk": 541828104, "platform": "yqq", "ct": 24, "cv": 0},
			                           "req": {"module": "QQConnectLogin.LoginServer", "method": "QQLogin",
			                                   "param": {
				                                   "code": MCQTSS_qzjwb(resp.headers['Location'], '&code=',
				                                                        '&state=state')}}},
			                     cookies=cookie.cookies, allow_redirects=False)
			cookie.cookies.update(resp.cookies)
			self.cookie = cookie.cookies.items()
			self.label_state.setText('登录成功,请点击完成登录保存')
			open('./MCQTSS/cookie.json', 'w+').write(json.dumps(self.cookie))
			QMessageBox.information(self, 'MCQTSS Music',
			                        'Cookie已保存到\n' + os.path.abspath(os.path.join('./MCQTSS', 'cookie.json')))


def time_to_seconds(time_str):
	# 使用正则表达式提取小时、分钟和秒
	time_pattern = r'\[(\d{2}):(\d{2}).(\d{2})\]'
	match = re.match(time_pattern, time_str)

	if match:
		minutes = int(match.group(1))
		seconds = int(match.group(2))
		seconds_min = int(match.group(3))
		total_seconds = float(minutes * 60 + seconds) + float('0.' + str(seconds_min))
		return total_seconds
	else:
		return None


class MainWindow(QMainWindow, Ui_Form_Main):
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)
		# 变量部分
		self.exit = None
		self.handle = None
		self.lyric_list = []
		self.min_s = -1
		self.min_s_last = 0.0
		# 窗口创建部分
		self.setWindowFlags(Qt.FramelessWindowHint)
		self.setAttribute(Qt.WA_TranslucentBackground)
		self.setupUi(self)
		# 记录鼠标按下时的位置
		self.drag_position = None
		# 初始化音乐封面
		self.inti_music_img()
		# 监听滑块滑动事件
		self.horizontalSlider_music_place.valueChanged.connect(self.modify_music_position)
		self.horizontalSlider_volume.valueChanged.connect(self.modify_volume)
		# 监听输入框事件
		self.lineEdit_search.installEventFilter(self)
		self.lineEdit_player_list.installEventFilter(self)
		# 隐藏quickbox
		self.groupBox_quick_box.hide()
		# 设置链接可被点击
		self.label_about_md.setOpenExternalLinks(True)
		# 按键绑定
		self.label_close.mousePressEvent = partial(self.close_pro, self.label_close)
		self.label_search.mousePressEvent = partial(self.switch_page, self.label_search)
		self.label_player_list.mousePressEvent = partial(self.switch_page, self.label_player_list)
		self.label_player.mousePressEvent = partial(self.switch_page, self.label_player)
		self.label_setting.mousePressEvent = partial(self.switch_page, self.label_setting)
		self.label_play_main_2.mousePressEvent = partial(self.play_click, self.label_play_main_2)
		self.label_play_main.mousePressEvent = partial(self.play_click, self.label_play_main)
		self.label_search_music.mousePressEvent = partial(self.search, self.label_search_music)
		self.label_search_player_list.mousePressEvent = partial(self.player_list, self.label_search_player_list)
		self.label_singer_player_2.mousePressEvent = partial(self.show_album_desc, self.label_singer_player_2)
		self.listView_lyric.clicked.connect(self.item_click_lyric)
		self.listView_search.clicked.connect(self.item_click_search)
		self.listView_player_list.clicked.connect(self.item_click_player_list)
		self.pushButton_QQLogin.clicked.connect(self.open_qq_login)
		self.checkBox_translate.clicked.connect(self.trans_click)
		self.checkBox_auto_play.clicked.connect(self.auto_play_click)
		# 创建文件夹
		try:
			os.makedirs('./MCQTSS')
		except FileExistsError:
			pass
		# 初始化BASS
		Bass.Init()
		self.label_bass_version.setText(f'播放组件版本:{Bass.GetVersion()}')
		# 测试类,正式需要注释
		# self.lyric_test()
		# self.bass_test()
		# self.play_music(1905521)
		# 初始化进度刷新线程
		threading.Thread(target=self.thr_music_time_ref).start()
		threading.Thread(target=self.lyric_ref_thr).start()
		threading.Thread(target=self.load).start()

	def load(self):
		# 加载传递参数和程序配置
		self.lineEdit_player_list.setText(MCQTSSConfig('player_list').get)
		self.player_list()
		try:
			self.horizontalSlider_volume.setValue(int(MCQTSSConfig('volume').get))
		except (TypeError, ValueError):
			self.horizontalSlider_volume.setValue(100)
		if play_info[0] == 1:
			self.play_music(play_info[1])
		elif play_info[0] == 2:
			self.search(play_info[1])
			self.switch_page(self.label_search, None)
		elif play_info[0] == 0:
			self.play_music(play_info[1])
			self.search(play_info[2])
		else:
			self.lineEdit_search.setText(MCQTSSConfig('search').get)
			self.search()
			if MCQTSSConfig('auto_play').get in [1, '1']:
				self.checkBox_auto_play.setChecked(True)
				try:
					self.play_music(int(MCQTSSConfig('music_id').get))
				except (ValueError, TypeError):
					pass
			if MCQTSSConfig('trans').get in [1, '1']:
				self.checkBox_translate.setChecked(True)

	def thr_music_time_ref(self):
		while True:
			if self.exit:
				return '/'
			time.sleep(0.5)
			if self.handle is None:
				continue
			all_seconds = BassChannel.GetLengthSeconds(self.handle, BassChannel.GetLengthBytes(self.handle))
			now_seconds = BassChannel.GetPositionSeconds(self.handle)
			self.horizontalSlider_music_place.blockSignals(True)
			self.horizontalSlider_music_place.setValue(int(now_seconds / all_seconds * 1000))
			self.horizontalSlider_music_place.blockSignals(False)
			minutes, seconds = divmod(all_seconds, 60)
			mtime = f"{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
			self.label_music_time_all.setText(mtime)
			minutes, seconds = divmod(now_seconds, 60)
			self.label_music_time_now.setText(f'{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}')
			if f'{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}' == mtime:
				BassChannel.Play(self.handle, True)

	def lyric_ref_thr(self):
		while True:
			time.sleep(0.1)
			if self.exit:
				return '/'
			if self.lyric_list is []:
				continue
			lyric = ''
			for line in self.lyric_list:
				if self.min_s == -1:
					self.select_row_by_extra_int(0.0)
					self.listView_lyric.update()
					self.min_s = 0.0
				if line['time'] < BassChannel.GetPositionSeconds(self.handle):
					self.min_s = line['time']
					lyric = line['lyric']
			if self.min_s != self.min_s_last:
				print(self.min_s, self.min_s_last, lyric)
				self.select_row_by_extra_int(self.min_s)
				self.listView_lyric.update()
				self.min_s_last = self.min_s

	def select_row_by_extra_int(self, target_extra_int):
		# 获取现有模型
		model = self.listView_lyric.model()
		if model is None:
			return

		for row in range(model.rowCount()):
			item = model.item(row)
			if item is not None:
				extra_int = item.data()  # 获取额外整数值
				if extra_int == target_extra_int:
					# 选中匹配的行
					selection_model = self.listView_lyric.selectionModel()
					selection_model.clearSelection()
					index = model.index(row, 0)
					selection_model.select(index, QItemSelectionModel.Select)

					# 滚动到匹配的行
					self.listView_lyric.scrollTo(index, QAbstractItemView.PositionAtCenter)

	def switch_page(self, label, event):
		if label != self.label_player:
			self.groupBox_quick_box.show()
		else:
			self.groupBox_quick_box.hide()
		if label == self.label_search:
			self.tabWidget_main.setCurrentIndex(1)
		elif label == self.label_player_list:
			self.tabWidget_main.setCurrentIndex(2)
		elif label == self.label_player:
			self.tabWidget_main.setCurrentIndex(0)
		elif label == self.label_setting:
			# QMessageBox.information(self, '温馨提示', '这个页面没写完(')
			self.tabWidget_main.setCurrentIndex(4)

	def modify_music_position(self, value):
		print("当前值:", value)
		BassChannel.SetPositionByBytes(self.handle,
		                               int(int(BassChannel.GetLengthBytes(self.handle)) * int(value) / 1000))

	def modify_volume(self, value):
		print('设置音量', value)
		Bass.ChannelSetAttribute(self.handle, value / 100)
		MCQTSSConfig('volume', value).set
		self.label_volume.setText(f'音量:{value}%')

	def inti_music_img(self):
		img = base64.b64encode(requests.get(
			'https://y.qq.com/music/photo_new/T002R300x300M000003jpkCG0OOSea_1.jpg?max_age=2592000').content).decode()
		self.label_music_img_payer.setText(
			f'<html><head/><body><p><img width="100" height="100"src="data:application/octet-stream;base64,{img}"/></p></body></html>')
		self.label_music_img_box.setText(
			f'<html><head/><body><p><img width="70" height="70"src="data:application/octet-stream;base64,{img}"/></p></body></html>')
		self.label_play_main_2.setText(
			f'<html><head/><body><p><img width="30" height="30" id="play" src="{MCQTSS_resource().img_play}"/></p></body></html>')
		self.label_play_main.setText(
			f'<html><head/><body><p><img width="40" height="40" id="play" src="{MCQTSS_resource().img_play}"/></p></body></html>')

	def play_click(self, label, event):
		if self.handle is None:
			return
		active = BassChannel.IsActive(self.handle)
		if active == 1:
			BassChannel.Pause(self.handle)
			self.label_play_main_2.setText(
				f'<html><head/><body><p><img width="30" height="30" id="play" src="{MCQTSS_resource().img_play}"/></p></body></html>')
			self.label_play_main.setText(
				f'<html><head/><body><p><img width="40" height="40" id="play" src="{MCQTSS_resource().img_play}"/></p></body></html>')
		elif active == 3:
			BassChannel.Play(self.handle, False)
			self.label_play_main_2.setText(
				f'<html><head/><body><p><img width="30" height="30" id="play" src="{MCQTSS_resource().img_stop}"/></p></body></html>')
			self.label_play_main.setText(
				f'<html><head/><body><p><img width="40" height="40" id="play" src="{MCQTSS_resource().img_stop}"/></p></body></html>')

	def search(self, label=None, event=None):
		self.listView_search.setModel(None)

		if isinstance(label, str):
			text = label
			self.lineEdit_search.setText(text)
		elif not (text := self.lineEdit_search.text()):
			return

		for line in QQ_Music().search_music_2(text, 50):
			print('*' * 20)
			print(line['title'])
			print(line['singer'][0]['title'])
			print(line['id'])
			print(line['mid'])
			print('*' * 20)

			desc = f"({line['desc']})" if line['desc'] else ''
			self.add_search(f"{line['name']}{desc}-{line['singer'][0]['name']}", line['id'])

		MCQTSSConfig('search', text).set

	def player_list(self, label=None, event=None):
		if not self.lineEdit_player_list.text():
			return

		self.listView_player_list.setModel(None)
		resp = self.type_check(self.lineEdit_player_list.text())

		if resp['code'] == -1:
			QMessageBox.warning(self, 'MCQTSS Music', '请输入正确的歌单ID或专辑Mid或当前类型不受支持')
			return

		elif resp['code'] == 1:
			try:
				for line in QQ_Music().get_playlist_info(resp['message'])['songList']:
					subtitle = line['subtitle'] or ''
					self.add_player_list(f"{line['name']}({subtitle})-{line['singer'][0]['name']}", line['id'])
				QMessageBox.information(self, 'MCQTSS Music', '由于QQ音乐限制,默认只能获取10条')
			except TypeError:
				QMessageBox.warning(self, 'MCQTSS Music', f'未找到当前歌单ID: {resp["message"]}')

		elif resp['code'] == 2:
			try:
				for line in QQ_Music().get_album_list(resp['message']):
					song_info = line['songInfo']
					subtitle = song_info['subtitle'] or ''
					self.add_player_list(f"{song_info['title']}({subtitle})-{song_info['singer'][0]['name']}",
					                     song_info['id'])
			except TypeError:
				QMessageBox.warning(self, 'MCQTSS Music', f'未找到当前专辑Mid: {resp["message"]}')

		MCQTSSConfig('player_list', str(resp['message'])).set

	def type_check(self, text):
		if re.compile('[a-zA-z]+://[^\s]*').search(text):
			if text.find('playlist') != -1:
				return {'code': 1, 'message': text.split('/')[-1].split('?')[0]}
			elif text.find('albumDetail') != -1:
				return {'code': 2, 'message': text.split('/')[-1].split('?')[0]}
			else:
				try:
					mid = re.findall('"albumMid":"(.*?)","albumName"', requests.get(text, headers=self.handle).text)
					if mid is []:
						return {'code': -1, 'message': 'Error'}
					return {'code': 2, 'message': mid[0]}
				except AttributeError:
					return {'code': -1, 'message': 'Error'}
		else:
			try:
				return {'code': 1, 'message': int(text)}
			except:
				return {'code': 2, 'message': text}

	def add_lyric(self, name, extra_int):
		# 获取现有模型
		model = self.listView_lyric.model()  # 获取已有的模型
		if model is None:
			model = QStandardItemModel()
			self.listView_lyric.setModel(model)

		item = QStandardItem(name)
		font = QFont()
		font.setBold(True)
		item.setForeground(QColor(192, 192, 192))
		item.setFont(font)
		font_metrics = QFontMetrics(font)
		item_size = QSize(font_metrics.width(name), 30)
		item.setSizeHint(item_size)

		# 存储额外整数值
		item.setData(extra_int)

		model.appendRow(item)

	def add_search(self, name, music_id):
		# 获取现有模型
		model = self.listView_search.model()  # 获取已有的模型
		if model is None:
			model = QStandardItemModel()
			self.listView_search.setModel(model)

		item = QStandardItem(name)
		font = QFont()
		font.setBold(True)
		item.setFont(font)
		font_metrics = QFontMetrics(font)
		item_size = QSize(font_metrics.width(name), 30)
		item.setSizeHint(item_size)

		# 存储额外整数值
		item.setData(music_id)

		model.appendRow(item)

	def add_player_list(self, name, music_id):
		# 获取现有模型
		model = self.listView_player_list.model()  # 获取已有的模型
		if model is None:
			model = QStandardItemModel()
			self.listView_player_list.setModel(model)

		item = QStandardItem(name)
		font = QFont()
		font.setBold(True)
		item.setFont(font)
		font_metrics = QFontMetrics(font)
		item_size = QSize(font_metrics.width(name), 30)
		item.setSizeHint(item_size)

		# 存储额外整数值
		item.setData(music_id)

		model.appendRow(item)

	def lyric_load(self, mid):
		lyric_main = False
		self.lyric_list = []
		self.listView_lyric.setModel(None)
		i = 0
		try:
			lyric = QQ_Music().get_lyrics_info(mid, MCQTSSConfig('trans').get)
			no_tran = lyric[0].split('\n')
			for line in lyric[1].split('\n'):
				i += 1
				if line.find('//') != -1:
					line = no_tran[i - 1]
				line = line.replace('\r', '')
				if line.find('[offset:0]') != -1:
					lyric_main = True
					continue
				if line.find('[00:00:00]') != -1:
					lyric_main = True
				if lyric_main:
					if time_to_seconds(line.split(']')[0] + ']') is not None and line.split(']')[1] != '':
						self.lyric_list.append({'time': time_to_seconds(line.split(']')[0] + ']'),
						                        'lyric': line.split(']')[1]})
						self.add_lyric(line.split(']')[1], time_to_seconds(line.split(']')[0] + ']'))
		except KeyError:
			self.lyric_list.append({'time': 0.0, 'lyric': '暂无歌词或歌词获取失败'})
			self.add_lyric('暂无歌词或歌词获取失败', 0.0)
		self.min_s = -1
		self.min_s_last = 0.0
		print(self.lyric_list)

	def item_click_lyric(self, index):
		item = index.model().itemFromIndex(index)
		extra_int = item.data()  # 获取额外整数值
		print(f"Clicked item: {item.text()}, Extra Integer: {extra_int}")

	def item_click_search(self, index):
		item = index.model().itemFromIndex(index)
		extra_int = item.data()  # 获取额外整数值
		print(f"Clicked item: {item.text()}, Extra Integer: {extra_int}")
		self.play_music(extra_int)

	def item_click_player_list(self, index):
		item = index.model().itemFromIndex(index)
		extra_int = item.data()  # 获取额外整数值
		print(f"Clicked item: {item.text()}, Extra Integer: {extra_int}")
		self.play_music(extra_int)

	def play_music(self, music_id):
		info = QQ_Music().get_music_info(music_id)[0]
		MCQTSSConfig('music_id', f'{music_id}').set
		img_id = info['album']['pmid']
		img = base64.b64encode(requests.get(
			f'https://y.qq.com/music/photo_new/T002R300x300M000{img_id}.jpg?max_age=2592000').content).decode()
		self.label_music_img_payer.setText(
			f'<html><head/><body><p><img width="100" height="100"src="data:application/octet-stream;base64,{img}"/></p></body></html>')
		self.label_music_img_box.setText(
			f'<html><head/><body><p><img width="70" height="70"src="data:application/octet-stream;base64,{img}"/></p></body></html>')
		name = info['name']
		self.label_music_name_box.setText(
			f'<html><head/><body><p><span style=" font-size:11pt; font-weight:600;">{name}</span></p></body></html>')
		self.label_music_name_player.setText(
			f'<html><head/><body><p><span style=" font-size:12pt; font-weight:600;">{name}</span></p></body></html>')
		self.label_singer_player.setText(info['singer'][0]['title'])
		album_info = QQ_Music().get_album_info(info['album']['mid'])['req_1']['data']['basicInfo']
		if album_info['desc'] == '':
			self.label_singer_player_2.setText(
				'<html><head/><body><p><span style=" color:#9f9f9f;">专辑简介:无</span></p></body></html>')
		else:
			desc = album_info['desc']
			self.label_singer_player_2.setText(
				f'<html><head/><body><p><span style=" color:#9f9f9f;">专辑简介:{desc}</span></p></body></html>')
		mid = info['mid']
		music_url = QQ_Music().get_music_url(mid).replace('\n', '')
		if music_url in ['', 'Error', 'https://dl.stream.qqmusic.qq.com/']:
			QMessageBox.warning(self, 'MCQTSS Music',
			                    '解析音乐下载链接时发生一个异常,可能当前音乐需要VIP或无法在网页播放')
			return
		local_path = os.path.abspath(os.path.join('./MCQTSS', os.path.basename(music_url).split('?')[0]))
		if not os.path.exists(local_path):
			try:
				if Downloader(music_url, 16, None).download() == 'Error':
					try:
						with open(local_path, 'wb+') as fh:
							fh.write(requests.get(music_url).content)
					except Exception as e:
						QMessageBox.warning(self, 'MCQTSS Music',
						                    f'播放器无法下载音乐,错误原因:{e}')
						return
			except requests.exceptions.HTTPError as e:
				QMessageBox.warning(self, 'MCQTSS', f'获取音乐URL失败\n{e}')
				return
		if self.handle is not None:
			BassStream.Free(self.handle)
			self.handle = None
		self.handle = BassStream.CreateFile(False, local_path.encode())
		try:
			Bass.ChannelSetAttribute(self.handle, int(MCQTSSConfig('volume').get))
		except:
			pass
		print('handle', self.handle)
		print('mid', mid)
		retval = BassChannel.Play(self.handle, True)
		if retval is not True:
			QMessageBox.warning(self, 'MCQTSS Music', '播放音乐时发生了一个异常,音乐文件无法被播放或初始化失败')
			return '/'
		self.lyric_load(mid)
		self.label_play_main_2.setText(
			f'<html><head/><body><p><img width="30" height="30" id="play" src="{MCQTSS_resource().img_stop}"/></p></body></html>')
		self.label_play_main.setText(
			f'<html><head/><body><p><img width="40" height="40" id="play" src="{MCQTSS_resource().img_stop}"/></p></body></html>')
		self.groupBox_quick_box.hide()
		self.tabWidget_main.setCurrentIndex(0)

	def show_album_desc(self, label=None, event=None):
		QMessageBox.information(self, '专辑介绍', MCQTSS_qzjwb(self.label_singer_player_2.text(),
		                                                       '<html><head/><body><p><span style=" color:#9f9f9f;">',
		                                                       '</span></p></body></html>'))

	def trans_click(self):
		if self.checkBox_translate.isChecked():
			MCQTSSConfig('trans', 1).set
		else:
			MCQTSSConfig('trans', 0).set

	def auto_play_click(self):
		if self.checkBox_auto_play.isChecked():
			MCQTSSConfig('auto_play', 1).set
		else:
			MCQTSSConfig('auto_play', 0).set

	def open_qq_login(self):
		qq_login = QQ_Login()
		qq_login.show()

	def close_pro(self, label, event):
		self.exit = True
		if self.handle is not None:
			Bass.Free()
			self.handle = None
		self.close()
		app.quit()
		sys.exit()

	def paintEvent(self, event):
		painter = QPainter(self)
		painter.setRenderHint(QPainter.Antialiasing)
		painter.setBrush(QBrush(Qt.white))
		painter.drawRoundedRect(self.rect(), 15, 15)

	def mousePressEvent(self, event):
		# 记录鼠标按下的位置
		self.drag_position = event.globalPos() - self.pos()

	def mouseMoveEvent(self, event):
		if self.drag_position is not None:
			# 移动窗口到新的位置
			self.move(event.globalPos() - self.drag_position)

	def mouseReleaseEvent(self, event):
		# 清除鼠标按下的位置
		self.drag_position = None

	def eventFilter(self, source, event):  # 监听回车搜索事件
		if event.type() == event.KeyPress:
			if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
				if source is self.lineEdit_search:
					self.search()
				elif source is self.lineEdit_player_list:
					self.player_list()
				return True  # Event is handled

		return super().eventFilter(source, event)


if __name__ == "__main__":
	QGuiApplication.setAttribute(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
	app = QApplication(sys.argv)
	try:
		from pybass3_mcqtss import *
	except (ImportError, FileNotFoundError, NameError) as e:
		QMessageBox.warning(None, "MCQTSS Music",
		                    "无法加载必要组件\n"
		                    "Windows系统请检查目录下是否存在bass.dll,bass_aac.dll,tags.dll\n"
		                    f"Linux系统请检查目录下是否存在libbass.so,libbass_aac.so,libtags.so\n错误信息:\n{e}")
		sys.exit()
	except Exception as e:
		QMessageBox.warning(None, "MCQTSS Music",
		                    "无法加载必要组件\n"
		                    f"请检查系统是否为X86_64或查看错误信息解决\n错误信息:\n{e}")
		sys.exit()
	play_info = [-1]
	try:
		arg()
		window = MainWindow()
		window.show()
	except Exception as e:
		QMessageBox.warning(None, 'MCQTSS Music', f'运行时发生了一个错误,错误信息:\n{e}')
	sys.exit(app.exec_())
