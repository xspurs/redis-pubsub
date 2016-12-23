# coding: utf-8

from autobahn.asyncio.websocket import WebSocketServerProtocol, \
	WebSocketServerFactory
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

class MyServerProtocol(WebSocketServerProtocol):
	def onConnect(self, request):
		print('Client connecting: {0}'.format(request.peer))
	def onOpen(self):
		print('WebSocket connetion open.')
	def onMessage(self, payload, isBinary):
		if isBinary:
			print('Binary message received: {0} bytes'.format(len(payload)))
		else:
			print('Text message received: {0}'.format(payload.decode('utf8')))
	def onClose(self, wasClean, code, reason):
		print('WebSocket connection closed: {0}'.format(reason))

# http server host
define('http_host', default='0.0.0.0', help='run http server on the given host', type=str)
# http server port
define('http_port', default=8000, help='run http server on the given port', type=int)
# socket server host
define('socket_host', default='0.0.0.0', help='run socket server on the given host', type=str)
# socket server port
define('socket_port', default=9000, help='run socket server on the given port', type=int)
# redis host
define('redis_host', default='127.0.0.1', help='the redis host to connect', type=str)
# redis port
define('redis_port', default=6379, help='the redis port to use', type=int)
# redis db(0 ~ 15)
define('redis_db', default=0, help='the redis db to use', type=int)
# redis password
define('redis_password', default=None, help='the redis password use to authenticate', type=str)
# channel to publish/subscribe
define('redis_channel', default='gChannel', help='the redis channel to pub & sub', type=str)


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

def get_websocket_url(host, port):
	template = u'ws://{host}:{port}'
	return template.format(host=host, port=port)


def main():
	# parse command line params
	tornado.options.parse_command_line()
	# create http server
	http_server = tornado.httpserver.HTTPServer(Application())
	# serve the host and port pass by command line(or default 0.0.0.0:8000)
	http_server.listen(options.http_port, options.http_host)

	# socket server
	import asyncio

	factory = WebSocketServerFactory(get_websocket_url(options.socket_host, options.socket_port))
	factory.protocol = MyServerProtocol

	loop = asyncio.get_event_loop()
	coro = loop.create_server(factory, options.socket_host, options.socket_port)
	server = loop.run_until_complete(coro)
	
	try:
		# start socket server
		loop.run_forever()
		# start http server
		tornado.ioloop.IOLoop.current().start()
	except KeyboardInterrupt:
		server.close()
		loop.close()
		print('Server Terminated By <C-c>.')


if __name__ == '__main__':
	main()
