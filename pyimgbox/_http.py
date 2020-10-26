import httpx

import logging  # isort:skip
log = logging.getLogger('pyimgbox')


class HTTPClient:
    def __init__(self):
        self._client = httpx.AsyncClient()
        self._headers = {}

    @property
    def headers(self):
        return self._headers

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def close(self):
        await self._client.aclose()

    async def get(self, url, params={}, json=False):
        response = await self._catch_errors(
            request=self._client.build_request(
                method='GET',
                url=url,
                headers=self._headers,
                params=params,
            ),
        )
        if json:
            return response.json()
        else:
            return response.text

    async def post(self, url, data={}, files={}, json=False):
        response = await self._catch_errors(
            request=self._client.build_request(
                method='POST',
                url=url,
                headers=self._headers,
                data=data,
                files=files,
            ),
        )
        if json:
            return response.json()
        else:
            return response.text

    async def _catch_errors(self, request):
        log.debug('Sending %r', request)

        # Don't send User-Agent
        if 'User-Agent' in request.headers:
            del request.headers['User-Agent']

        try:
            response = await self._client.send(request)

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 413:
                    raise ConnectionError(f'{request.url}: File too large')
                else:
                    print(repr(response.text))
                    raise ConnectionError(f'{request.url}: {response.text}')

        except httpx.InvalidURL as e:
            print(type(e), e)
            raise ConnectionError(f'{request.url}: Invalid URL')

        except httpx.TimeoutException as e:
            print(type(e), e)
            print(dir(e))
            raise ConnectionError(f'{request.url}: Timeout')

        except httpx.NetworkError as e:
            print(type(e), e)
            print(dir(e))
            raise ConnectionError(f'{request.url}: Connection failed')

        except httpx.HTTPError as e:
            print(type(e), e)
            print(dir(e))
            raise ConnectionError(f'{request.url}: {e}')

        else:
            return response
