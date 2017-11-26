""" Logging numpy and python scalars to tensorboard.

Works directly with python/numpy types, doesn't require tensorflow ops/sess.

#####

This is a modified version of https://gist.github.com/gyglim/1f8dfb1b5c82627ae3efcfbbadb9f514
Original author: Michael Gygli.)
License: Copyleft

Notable modifications:
- Ported to python 3.6
- Initializing TensorBoardLogger with always_flush flushes after every log
  (directly writing to disk)
- log_image() wrapper for logging a single image
- Color map support in image logging
- Minor style changes
- Type hints
"""

from io import BytesIO
from numbers import Number
from typing import Union, Sequence

import tensorflow as tf
import matplotlib.pyplot as plt
import numpy as np

class TensorBoardLogger:
    """Logging in tensorboard without tensorflow ops."""

    writer: tf.summary.FileWriter
    log_dir: str
    always_flush: bool

    def __init__(self, log_dir: str, always_flush: bool = False) -> None:
        """Create a summary writer logging to log_dir."""
        self.writer = tf.summary.FileWriter(log_dir)
        self.always_flush = always_flush

    def log_scalar(self, tag: str, value: Number, step: int) -> None:
        """Log a scalar variable.

        Parameters
        ----------
        tag
            Name of the scalar
        value
            Scalar value to be logged
        step
            training iteration
        """
        summary = tf.Summary(
            value=[tf.Summary.Value(tag=tag, simple_value=value)]
        )
        self.writer.add_summary(summary, step)
        if self.always_flush:
            self.writer.flush()

    def log_images(
        self,
        tag: str,
        images: Sequence[np.ndarray],
        step: int,
        cmap='gray'
        ) -> None:
        """Logs a list of images."""

        im_summaries = []
        for i, img in enumerate(images):
            # Write the image to a bytestring
            image_bytes = BytesIO()
            plt.imsave(image_bytes, img, format='png', cmap=cmap)

            # Create an Image object
            img_sum = tf.Summary.Image(
                encoded_image_string=image_bytes.getvalue(),
                height=img.shape[0],
                width=img.shape[1]
            )
            # Create a Summary value
            im_summaries.append(tf.Summary.Value(tag='%s/%d' % (tag, i),
                                                 image=img_sum))

        # Create and write Summary
        summary = tf.Summary(value=im_summaries)
        self.writer.add_summary(summary, step)
        if self.always_flush:
            self.writer.flush()

    def log_image(self, tag: str, image: np.ndarray, *args, **kwargs) -> None:
        self.log_images(tag, [image], *args, **kwargs)

    def log_histogram(
        self,
        tag: str,
        values: Union[Sequence[Number], np.ndarray],
        step: int,
        bins: int = 1000
        ) -> None:
        """(Not yet tested!) Logs the histogram of a list/vector of values."""
        # Convert to a numpy array
        values = np.array(values)

        # Create histogram using numpy
        counts, bin_edges = np.histogram(values, bins=bins)

        # Fill fields of histogram proto
        hist = tf.HistogramProto()
        hist.min = float(np.min(values))
        hist.max = float(np.max(values))
        hist.num = int(np.prod(values.shape))
        hist.sum = float(np.sum(values))
        hist.sum_squares = float(np.sum(values**2))

        # Requires equal number as bins, where the first goes from -DBL_MAX to bin_edges[1]
        # See https://github.com/tensorflow/tensorflow/blob/master/tensorflow/core/framework/summary.proto#L30
        # Thus, we drop the start of the first bin
        bin_edges = bin_edges[1:]

        # Add bin edges and counts
        for edge in bin_edges:
            hist.bucket_limit.append(edge)
        for c in counts:
            hist.bucket.append(c)

        # Create and write Summary
        summary = tf.Summary(value=[tf.Summary.Value(tag=tag, histo=hist)])
        self.writer.add_summary(summary, step)
        if self.always_flush:
            self.writer.flush()