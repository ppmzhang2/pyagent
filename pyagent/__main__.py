import sys
from typing import Optional

import pyagent.client_server as client
import pyagent.proxy_server as server

args = sys.argv[1:]

funcs = {'server': (0, server.run), 'client': (0, client.run)}


def request() -> Optional[str]:
    """get the input request string, which will be then mapped as key to get
    main method

    :return:
    """
    try:
        return str(args[0])
    except IndexError:
        return None


def main() -> None:
    if request() is None:
        raise TypeError('expect at least one input')

    n_args, func = funcs.get(request(), (None, None))

    if func is None:
        raise TypeError('input request is not valid, accept only {}'.format(
            list(funcs.keys())))

    if n_args == 0:
        func()
    else:
        raise TypeError('input error')


if __name__ == '__main__':
    main()
