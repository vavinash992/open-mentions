from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from tqdm import tqdm


def run_in_parallel(func: Callable[..., Any], args_list: list[tuple[Any, Any]], max_workers: int = 3) -> list[Any]:
    """
    Run a function in parallel using a thread pool executor.

    Args:
        func (callable): The function to run in parallel.
        args_list (list): A list of arguments to pass to the function.
        max_workers (int): The maximum number of threads to use.

    Returns:
        list: A list of results from the function calls.
    """
    if not callable(func):
        msg = "The first argument must be a callable function."
        raise TypeError(msg)
    max_workers = max(1, max_workers)
    results: list[Any] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_args = {executor.submit(func, *args): args for args in args_list}
        for future in tqdm(as_completed(future_to_args), total=len(args_list)):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Error processing {future_to_args[future]}: {e}")
    return results
