# Copyright (c) 2020 Nekokatt
# Copyright (c) 2021-present davfsa
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Asyncio extensions and utilities."""

from __future__ import annotations

__all__: typing.Sequence[str] = ("all_of", "completed_future", "destroy_loop", "first_completed", "get_or_make_loop")

import asyncio
import typing
import warnings

if typing.TYPE_CHECKING:
    import logging

T_co = typing.TypeVar("T_co", covariant=True)
T_inv = typing.TypeVar("T_inv")


def completed_future(result: T_inv | None = None, /) -> asyncio.Future[T_inv | None]:
    """Create a future on the current running loop that is completed, then return it.

    Parameters
    ----------
    result
        The value to set for the result of the future.
        [`T_inv`][] is a generic type placeholder for the type that
        the future will have set as the result. `T_inv` may be [`None`][],
        in which case, this will return [`asyncio.Future`][][[`None`][]].

    Returns
    -------
    asyncio.Future[T_inv]
        The completed future.

    Raises
    ------
    RuntimeError
        When called in an environment with no running event loop.
    """
    future = asyncio.get_running_loop().create_future()
    future.set_result(result)
    return future


async def first_completed(*aws: typing.Awaitable[typing.Any], timeout: float | None = None) -> None:
    """Wait for the first awaitable to complete.

    The awaitables that don't complete first will be cancelled.

    Completion is defined as having a result or an exception set. Thus,
    cancelling any of the awaitables will also result in the others being
    cancelled.

    If the first awaitable raises an exception, then that exception will be
    propagated.

    !!! note
        If more than one awaitable is completed before entering this call, then
        the first future is always returned.

    Parameters
    ----------
    *aws
        Awaitables to wait for.
    timeout
        Optional timeout to wait for, or [`None`][] to not use one.
        If the timeout is reached, all awaitables are cancelled immediately.
    """
    fs = tuple(map(asyncio.ensure_future, aws))
    iterator = asyncio.as_completed(fs, timeout=timeout)

    try:
        await next(iterator)
    except asyncio.CancelledError:
        msg = "first_completed gatherer cancelled"
        raise asyncio.CancelledError(msg) from None
    except asyncio.TimeoutError:
        msg = "first_completed gatherer timed out"
        raise asyncio.TimeoutError(msg) from None
    finally:
        for f in fs:
            if not f.done() and not f.cancelled():
                f.cancel()
                # Asyncio gathering futures complain if not awaited after cancellation
                try:
                    await f
                except asyncio.CancelledError:
                    pass


async def all_of(*aws: typing.Awaitable[T_co], timeout: float | None = None) -> typing.Sequence[T_co]:
    """Await the completion of all the given awaitable items.

    If any fail or time out, then they are all cancelled.

    Parameters
    ----------
    *aws
        Awaitables to wait for.
    timeout
        Optional timeout to wait for, or [`None`][] to not use one.
        If the timeout is reached, all awaitables are cancelled immediately.

    Returns
    -------
    typing.Sequence[T_co]
        The results of each awaitable in the order they were invoked in.
    """
    fs: tuple[asyncio.Future[T_co], ...] = tuple(map(asyncio.ensure_future, aws))
    gatherer = asyncio.gather(*fs)

    try:
        return await asyncio.wait_for(gatherer, timeout=timeout)
    except asyncio.TimeoutError:
        msg = "all_of gatherer timed out"
        raise asyncio.TimeoutError(msg) from None
    except asyncio.CancelledError:
        msg = "all_of gatherer cancelled"
        raise asyncio.CancelledError(msg) from None
    finally:
        for f in fs:
            if not f.done() and not f.cancelled():
                f.cancel()
                # Asyncio gathering futures complain if not awaited after cancellation
                try:
                    await f
                except asyncio.CancelledError:
                    pass

        gatherer.cancel()
        try:
            await gatherer
        except asyncio.CancelledError:
            pass


def get_or_make_loop() -> asyncio.AbstractEventLoop:
    """Get the current usable event loop or create a new one.

    Returns
    -------
    asyncio.AbstractEventLoop
        The requested loop.
    """
    # get_event_loop will error under oddly specific cases such as if set_event_loop has been called before even
    # if it was just called with None or if it's called on a thread which isn't the main Thread.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            loop = asyncio.get_event_loop_policy().get_event_loop()

        # Closed loops cannot be reused.
        if not loop.is_closed():
            return loop

    except RuntimeError:
        pass

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop


async def _gather(coros: typing.Iterator[typing.Awaitable[typing.Any]]) -> None:
    # Calling asyncio.gather outside of a running event loop isn't safe and
    # will lead to RuntimeErrors in later versions of python, so this call is
    # kept within a coroutine function.
    await asyncio.gather(*coros)


def destroy_loop(loop: asyncio.AbstractEventLoop, logger: logging.Logger) -> None:
    """Destroy the passed loop.

    Parameters
    ----------
    loop
        The loop to destroy
    logger
        The logger to use for logging
    """

    async def murder(future: asyncio.Future[typing.Any]) -> None:
        # These include _GatheringFuture which must be awaited if the children
        # throw an asyncio.CancelledError, otherwise it will spam logs with warnings
        # about exceptions not being retrieved before GC.
        try:
            logger.debug("killing %s", future)
            future.cancel()
            await future
        except asyncio.CancelledError:
            pass
        except Exception as ex:  # noqa: BLE001 - Do not catch blind exception
            loop.call_exception_handler(
                {
                    "message": "Future raised unexpected exception after requesting cancellation",
                    "exception": ex,
                    "future": future,
                }
            )

    remaining_tasks = tuple(t for t in asyncio.all_tasks(loop) if not t.done())

    if remaining_tasks:
        logger.warning("terminating %s remaining tasks forcefully", len(remaining_tasks))
        loop.run_until_complete(_gather(murder(task) for task in remaining_tasks))
    else:
        logger.debug("No remaining tasks exist, good job!")

    logger.debug("shutting down default executor")
    try:
        # This seems to raise a NotImplementedError when running with uvloop.
        loop.run_until_complete(loop.shutdown_default_executor())
    except NotImplementedError:
        pass

    logger.debug("shutting down asyncgens")
    loop.run_until_complete(loop.shutdown_asyncgens())

    logger.debug("closing event loop")
    loop.close()

    # Closed loops cannot be reused so it should also be un-set.
    asyncio.set_event_loop(None)
