if __name__ == "__main__":
    import sys
    import server
    import client
    import argparse
    from interface import Interface

    def parser():
        parser_main = argparse.ArgumentParser(description="Game Library Player")

        parser_optional = parser_main._action_groups.pop()
        parser_network = parser_main.add_argument_group('Network')
        parser_server = parser_main.add_argument_group('Server')
        parser_main._action_groups.append(parser_optional)

        parser_network.add_argument("-a", "--addr", dest="addr", type=str,
            help="IPv4 Address Override Settings")
        parser_network.add_argument("-p", "--port", dest="port", type=int,
            help="Port Number Override Settings")
        parser_network.add_argument("-w", "--web", dest="port", type=int,
            help="Webserver Port Number Override Settings")
        parser_server.add_argument("-s", "--server", dest="server", action="store_true",
            help="Host a Server Instance")
        parser_server.add_argument("--repop", dest="repopulate", action="store_true",
            help="Regenerate the Database")
        parser_server.add_argument("--headless", dest="no_client", action="store_true",
            help="Run without Client")
        return parser_main

    def main():
        args = parser().parse_args()
        if args.server:
            Interface.schedule(server.main(args.repopulate))
            if args.no_client:
                return
        client.main("127.0.0.1")
        Interface.stop()

    with Interface.main_thread():
        main()
