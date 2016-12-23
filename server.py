# coding: utf-8

from os import path
from sys import stdout

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.options import define, options

import redis
import logging.config
import logging


# server host
define('host', default='0.0.0.0', help='run on the given host', type=str)
# server port
define('port', default=8000, help='run on the given port', type=int)
# redis host
define('redis_host', default='127.0.0.1', help='the redis host to connect')
# redis port
define('redis_port', default=6379, help='the redis port to use', type=int)
# redis db(0 ~ 15)
define('redis_db', default=0, help='the redis db to use', type=int)
# redis password
define('redis_password', default=None, help='the redis password use to authenticate')
# channel to publish/subscribe
define('redis_channel', default='gChannel', help='the redis channel to pub & sub')


logger = logging.getLogger('root')
# handler that log to file
file_handler = logging.FileHandler('./server.log')
file_handler.setLevel(logging.INFO)
# handler that log to stdout
stream_handler = logging.StreamHandler(stdout)
stream_handler.setLevel(logging.INFO)
# add handlers, log to file and stdout simultaneously
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# extends tornado.web.Application
class Application(tornado.web.Application):
	def __init__(self):
		# register tornado's RequestHandler to designated context path
		handlers = [
			(r'/publish', PublishHandler),
			(r'/subscribe', SubscribeHandler), 
			(r'/', IndexHandler),
        	]
		settings = dict(
			template_path=path.join(path.dirname(__file__), 'templates'),
			static_path=path.join(path.dirname(__file__), 'static'),
		)
		super(Application, self).__init__(handlers, **settings)
		# redis singeleton to share among handlers
		self.redis = redis.StrictRedis(host=options.redis_host, port=options.redis_port, db=options.redis_db, password=options.redis_password)
		# redis pubsub singeleton to share among handler(pubsub is used to subscribe channels)
		self.pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
		self.pubsub.subscribe(options.redis_channel)
		# logger to record log
		self.logger = logger


# base handler
class BaseHandler(tornado.web.RequestHandler):
	@property
	def redis(self):  # get redis singleton in handler
		return self.application.redis
	@property
	def pubsub(self): # get redis pubsub singleton in handler
		return self.application.pubsub
	@property
	def logger(self): # get logger singleton in handler
		return self.application.logger


# demo page to loop /subscribe by ajax and setInterval
class IndexHandler(BaseHandler):
	def get(self):
		self.logger.info('===== access index-handler =====')
		self.logger.error(isinstance(self, tornado.web.RequestHandler))
		self.render('subscribe.html')


# publish message into channel
class PublishHandler(BaseHandler):
	def post(self):
		# set CORS for cross-origin request
		# CORS Beginning
		self.set_header('Access-Control-Allow-Origin', '*')
		self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
		self.set_header('Access-Control-Max-Age', 1000)
		self.set_header('Access-Control-Allow-Headers', '*')
		# CORS Ending

		type = self.get_argument('type').strip()
		# TODO 处理异常信息，如redis密码错误
		# ResponseError: NOAUTH Authentication required.
		try:
			return_code = self.redis.publish(options.redis_channel, type)
			if return_code > 0:
				self.set_status(200)
			else:
				self.set_status(500)
		except redis.ResponseError as e:
			# self.logger.error('===== error: ' + e + ' =====')
			self.logger.error(e)
			#logger.error(e)
            

class SubscribeHandler(BaseHandler):
	def get(self):
		# set CORS for cross-origin request
		# CORS Beginning
		self.set_header('Access-Control-Allow-Origin', '*')
		self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
		self.set_header('Access-Control-Max-Age', 1000)
		self.set_header('Access-Control-Allow-Headers', '*')
		# CORS Ending

		# TODO 改造该接口，可以穿入一个或多个channel进行subscribe
		#self.pubsub.subscribe(options.redis_channel)
		message = self.pubsub.get_message()
		if message and message.get('type') == 'message':
			self.write(str(message.get('data')))
		else:
			self.write('-1')


def main():
	tornado.options.parse_command_line()
	# create http server
	http_server = tornado.httpserver.HTTPServer(Application())
	# serve the host and port pass by command line(or default 0.0.0.0:8000)
	http_server.listen(options.port, options.host)
	# start http server
	tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt as ki:
		print('Server Terminated By <C-c>.')
