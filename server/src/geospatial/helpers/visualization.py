import matplotlib.pyplot as plt
from functools import wraps
from src.geospatial.lib.pygmtsar import Stack


def plot_and_save(plot_func, filename, *args, **kwargs):
    """
    Executes a plotting function and saves the resulting plot to a file.

    Parameters:
    - plot_func: callable
        The function that performs the plotting. It should accept *args and **kwargs.
    - filename: str
        The path to save the output file, including the extension.
    - *args, **kwargs:
        Arguments to be passed to the plotting function.

    Returns:
    - None
    """

    fig, ax = plt.subplots()
    print(args, kwargs)

    try:
        plot_func(ax, *args, **kwargs)
        fig.savefig(filename, dpi=300, bbox_inches="tight")
    finally:
        plt.close(fig)


def save_plot(func):
    """
    Decorator to save a plot after the function execution.

    The filepath will be passed dynamically from the decorated function.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        filepath = kwargs.get("filepath", "plot.png")
        result = func(*args, **kwargs)
        plt.savefig(filepath, bbox_inches="tight", dpi=300)
        plt.close()

        return result

    return wrapper


class ExtendedStack(Stack):
    @save_plot
    def plot_scenes(
        self,
        dem="auto",
        image=None,
        alpha=None,
        caption="Estimated Scene Locations",
        cmap="turbo",
        filepath=None,
        aspect=None,
        **kwargs,
    ):
        super().plot_scenes(
            dem=dem,
            image=image,
            alpha=alpha,
            caption=caption,
            cmap=cmap,
            aspect=aspect,
            **kwargs,
        )
