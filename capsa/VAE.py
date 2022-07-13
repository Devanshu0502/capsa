from random import sample
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

from utils.utils import Sampling, duplicate_layer


class VAEWrapper(keras.Model):
    def __init__(self, base_model, decoder, is_standalone=True, latent_dim=32):
        super(VAEWrapper, self).__init__()

        self.metric_name = "VAEWrapper"
        self.is_standalone = is_standalone

        if is_standalone:
            self.feature_extractor = tf.keras.Model(
                base_model.inputs, base_model.layers[-2].output
            )

        self.mean_layer = tf.keras.layers.Dense(latent_dim)
        self.log_std_layer = tf.keras.layers.Dense(latent_dim)
        self.sampling_layer = Sampling()

        last_layer = base_model.layers[-1]
        self.output_layer = duplicate_layer(last_layer)  # duplicate last layer

        self.decoder = decoder

    def reconstruction_loss(self, mu, log_std, y):

        sampled_latent_vector = self.sampling_layer([mu, log_std])

        # reconstruction loss:
        reconstruction = self.decoder(sampled_latent_vector)
        mse_loss = tf.reduce_mean(
            tf.reduce_sum(tf.math.square(reconstruction - y), axis=0)
        )
        kl_loss = -0.5 * tf.reduce_mean(
            1 + log_std - tf.math.square(mu) - tf.math.square(tf.math.exp(log_std)),
            axis=0,
        )
        return mse_loss + kl_loss

    def loss_fn(self, x, y, extractor_out=None):
        if self.is_standalone:
            extractor_out = self.feature_extractor(x, training=True)

        predictor_y = self.output_layer(extractor_out)

        compiled_loss = tf.reduce_mean(
            self.compiled_loss(y, predictor_y, regularization_losses=self.losses),
        )

        mu = self.mean_layer(extractor_out)
        log_std = self.log_std_layer(extractor_out)
        recon_loss = self.reconstruction_loss(mu=mu, log_std=log_std, y=y)
        return recon_loss + compiled_loss, predictor_y

    def train_step(self, data):
        x, y = data

        with tf.GradientTape() as t:
            loss, predictor_y = self.loss_fn(x, y)

        trainable_vars = self.trainable_variables
        gradients = t.gradient(loss, trainable_vars)
        self.optimizer.apply_gradients(zip(gradients, trainable_vars))
        self.compiled_metrics.update_state(y, predictor_y)
        return {m.name: m.result() for m in self.metrics}

    @tf.function
    def wrapped_train_step(self, x, y, extractor_out):
        with tf.GradientTape() as t:
            loss, predictor_y = self.loss_fn(x, y, extractor_out)

        trainable_vars = self.trainable_variables
        gradients = t.gradient(loss, trainable_vars)
        self.optimizer.apply_gradients(zip(gradients, trainable_vars))

        return tf.gradients(loss, extractor_out)

    def inference(self, x, extractor_out=None):
        if self.is_standalone:
            extractor_out = self.feature_extractor(x, training=False)

        mu = self.mean_layer(extractor_out)
        log_std = self.log_std_layer(extractor_out)

        out = self.output_layer(extractor_out)

        return out, mu, log_std
