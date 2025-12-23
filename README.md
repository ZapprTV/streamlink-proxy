# streamlink-proxy
streamlink-proxy is a very simple API that translates video links from [Streamlink-compatible websites](https://streamlink.github.io/plugins.html) to their direct streaming URL.

Find out more about it or start using our free hosted instance at [https://streamlink.zappr.stream](https://streamlink.zappr.stream/).

## How to self-host
You will need Python 3+ and Git installed.

Prepare your development environment:
1. `git clone https://github.com/ZapprTV/streamlink-proxy.git`
2. `cd streamlink-proxy`
3. `pip install -r requirements.txt`

Now, to run the actual server:
`uvicorn server:app --host 0.0.0.0 --port 8080 --loop uvloop --http httptools`