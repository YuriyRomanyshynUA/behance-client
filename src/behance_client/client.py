import asyncio
from scalpl import Cut
from .baseclient import BaseClient


class Behance(BaseClient):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def search(self, content="users", **kwargs):
        res = await self.get(
            "/search",
            params = {
                "content": content,
                **kwargs
            }
        )
        return await res.json()

    async def get_users(
        self,
        search="",
        country="",
        state="",
        state_code="",
        city="",
        school_id="",
        tool_id="",
        sort="recommended",
        ordinal="",
        **kwargs
    ):
        res = Cut(await self.search(
            content = "users",
            search = search,
            country = country,
            state = state,
            stateCode = state_code,
            city = city,
            schools = school_id,
            tools = tool_id,
            sort = sort,
            ordinal = ordinal,
            **kwargs
        ))
        return res['search.content.users'], {
            "hasMore": res['search.hasMore'],
            "itemsPerPage": res['search.itemsPerPage'],
            "nextOrdinal": res['search.nextOrdinal'],
            "nextPage": res["search.nextPage"]
        }

    async def load_users(
        self,
        start_from=0,
        pages_limit=None,
        preload_limit=1,
        errors_limit=0,
        full_res=False,
        sleep = None,
        **kwargs
    ):
        assert preload_limit > 0
        assert errors_limit > -1
        assert (pages_limit is None) or pages_limit > 0

        page = 1
        items_per_page = 48
        next_ordinal = start_from
        outer_loop_cond = True
        errors_count = 0
        tasks = None

        while outer_loop_cond:
            tasks = []

            for _ in range(preload_limit):
                tasks.append(asyncio.create_task(
                    self.search(
                        content = "users",
                        ordinal = next_ordinal,
                        **kwargs
                    )
                ))
                page += 1
                if pages_limit is not None and page > pages_limit:
                    outer_loop_cond = False
                    break
                else:
                    next_ordinal += items_per_page

            gather = await asyncio.gather(*tasks, return_exceptions=True)

            for r in gather:

                if isinstance(r, (AssertionError,)):
                    raise r from None
                if isinstance(r, (Exception,)):
                    errors_count += 1
                    if errors_count > errors_limit:
                        raise r from None
                    self.logger.info(
                        f"Error occured - {repr(r)}\n"
                        f"Errors count - {errors_count}"
                    )
                    break

                proxy = Cut(r)
                has_more = proxy['search.hasMore']
                next_ordinal = proxy['search.nextOrdinal']

                if full_res is True:
                    yield r
                else:
                    users = proxy['search.content.users']
                    for _ in users:
                        yield _

                if has_more is False:
                    self.logger.info("Has more false")
                    return

                if sleep:
                    await asyncio.sleep(sleep)

    async def get_user_projects(self, username, offset=12, full_res=False):
        res = await self.get(
            f"/{username}/projects",
            params = {"offset": offset}
        )

        if full_res:
            return await res.json()

        proxy = Cut(await res.json())
        return (
            proxy['profile.activeSection.work.projects'],
            proxy['profile.activeSection.work.hasMore']
        )

    async def load_user_projects(
        self,
        username,
        pages_limit=None,
        preload_limit=1,
        errors_limit=0,
        sleep=None
    ):
        assert preload_limit > 0
        assert errors_limit > -1
        assert (pages_limit is None) or pages_limit > 0

        outer_loop_cond = True
        errors_count = 0
        page = 1
        offset = 12
        tasks = None

        while outer_loop_cond:
            tasks = []

            for _ in range(preload_limit):
                tasks.append(asyncio.create_task(
                    self.get_user_projects(username, offset)
                ))
                page += 1
                offset += 12
                if pages_limit is not None and page > pages_limit:
                    outer_loop_cond = False
                    break

            gather = await asyncio.gather(*tasks, return_exceptions=True)

            for r in gather:

                if isinstance(r, (AssertionError,)):
                    raise r from None
                if isinstance(r, (Exception,)):
                    errors_count += 1
                    if errors_count > errors_limit:
                        raise r from None
                    self.logger.info(
                        f"Error occured - {repr(r)}\n"
                        f"Errors count - {errors_count}"
                    )
                    break

                projects, has_more = r

                for p in projects:
                    yield p

                if has_more is False:
                    return

            if sleep:
                await asyncio.sleep(sleep)
