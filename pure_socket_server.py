# coding: utf-8

from autobahn.asyncio.websocket import WebSocketServerProtocol, \
    WebSocketServerFactory

import tornado.options
from tornado.options import define, options


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

        self.sendMessage(payload, isBinary)

    def onClose(self, wasClean, code, reason):
        print('WebSocket connection closed: {0}'.format(reason))


# socket server host
define('socket_host', default='0.0.0.0', help='run socket server on the given host', type=str)
# socket server port
define('socket_port', default=9000, help='run socket server on the given port', type=int)


def get_websocket_url(host, port):
    template = u'ws://{host}:{port}'
    return template.format(host=host, port=port)


def main():
    # parse command line params
    tornado.options.parse_command_line()

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
    except KeyboardInterrupt:
        server.close()
        loop.close()
        print('Server Terminated By <C-c>.')


if __name__ == '__main__':
    main()
