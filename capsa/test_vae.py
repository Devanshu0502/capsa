import tensorflow as tf
from tensorflow.keras import layers

import numpy as np
import matplotlib.pyplot as plt

from wrapper import Wrapper
from VAE import VAEWrapper
from utils.utils import get_user_model, plt_vspan, plot_results, get_decoder
from data.regression import get_data_v1, get_data_v2


def test_vae(use_case=None):

    their_model = get_user_model()
    decoder = get_decoder()
    ds_train, x_val, y_val = get_data_v2(batch_size=256)

    ### use case 1 - user can interact with a MetricWrapper directly
    if use_case == 1:
        model = VAEWrapper(their_model, decoder)
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=2e-3),
            loss=tf.keras.losses.MeanSquaredError(),
        )
        history = model.fit(ds_train, epochs=30)

        plt.plot(history.history["loss"])
        plt.show()

        y_pred, mu, log_std = model.inference(x_val)

    ### use case 2 - user can interact with a MetricWrapper through Wrapper (what we call a "controller wrapper")
    elif use_case == 2:

        # make 'controller' wrapper behave like a tf model, such that user can interact with it
        # the same as they directly a any of the MetricWrappers (see 3 lines above)
        # so in controller Wrapper implement compile() and fit() methods
        model = Wrapper(their_model, metrics=[VAEWrapper])

        model.compile(
            # user needs to specify optim and loss for each metric
            optimizer=[tf.keras.optimizers.Adam(learning_rate=2e-3)],
            # note reduction needs to be NONE, model reduces to mean under the hood
            loss=[
                tf.keras.losses.MeanSquaredError(
                    reduction=tf.keras.losses.Reduction.NONE
                )
            ],
        )

        model.fit(ds_train, epochs=30)

        metrics_out = model.inference(x_val)
        y_pred, mu, log_std = metrics_out["HistogramWrapper"]

    fig, axs = plt.subplots(2)
    axs[0].scatter(x_val, y_val, s=0.5, label="gt")
    axs[0].scatter(x_val, y_pred, s=0.5, label="yhat")
    plt_vspan()
    plt.legend()
    plt.show()


test_vae(use_case=1)
