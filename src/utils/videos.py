import m3u8
import struct
import requests


class VideoDuration:
    def __init__(self, url, use_m3u8=False):
        self.url = url
        self.seek = 0
        self.duration = 0
        self.s = requests.session()
        self.timeout = 6
        self.use_m3u8 = use_m3u8
        self.s.headers = {
            'Connection': 'keep-alive',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36'
        }

    def _set_headers(self, seek, type):
        if type in ['moov', 'duration']:
            self.s.headers['Range'] = 'bytes={}-{}'.format(seek, seek + 7)

    def _send_request(self, url=None):
        try:
            data = self.s.get(url=url or self.url, stream=True if not self.use_m3u8 else False,
                              timeout=self.timeout)
            if self.use_m3u8:
                return data.content
            else:
                return data.raw.read()
        except requests.Timeout:
            raise "Request timeout"
        return data

    def _find_moov_request(self):
        self._set_headers(self.seek, type='moov')
        data = self._send_request()
        size = int(struct.unpack('>I', data[:4])[0])
        flag = data[-4:].decode('ascii')
        return size, flag

    def _find_duration_request(self):
        self._set_headers(seek=self.seek+4+4+20, type='duration')
        data = self._send_request()
        time_scale = int(struct.unpack('>I', data[:4])[0])
        duration = int(struct.unpack('>I', data[-4:])[0])
        return time_scale, duration

    def get_duration(self):
        if self.use_m3u8:
            playlist_data = self._send_request().decode('utf-8')
            lines = playlist_data.splitlines()
            for line in lines:
                if line.startswith("https"):
                    playlist_data = self._send_request(line).decode('utf-8')
                    playlist = m3u8.loads(playlist_data)
                    for segment in playlist.segments:
                        if segment.duration:
                            self.duration += segment.duration
                    return self.duration
        else:
            while True:
                size, flag = self._find_moov_request()
                if flag == 'moov':
                    time_scale, duration = self._find_duration_request()
                    self.duration = duration/time_scale
                    return self.duration
                else:
                    self.seek += size
