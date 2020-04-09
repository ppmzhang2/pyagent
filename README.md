# Python Agent

An anonymous TCP proxy with data encryption based on `asyncio`.

## Usage

Server side:

```shell script
python -m pyagent server
```

Client side:

```shell script
python -m pyagent client
```

## Reference

* https://gist.github.com/scturtle/7967cb4e7c2bb0f91ca5
* https://docs.python.org/3/library/asyncio-protocol.html#asyncio.Protocol.data_received
