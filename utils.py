import logging
import os

from hbconfig import Config
import tensorflow as tf


class Logger(object):
    class __Logger:
        def __init__(self):
            self._logger = logging.getLogger("crumbs")
            self._logger.setLevel(logging.INFO)

            formatter = logging.Formatter(
                '[%(levelname)s|%(filename)s:%(lineno)s] %(asctime)s > %(message)s')

            streamHandler = logging.StreamHandler()
            streamHandler.setFormatter(formatter)

            self._logger.addHandler(streamHandler)

    instance = None

    def __init__(self):
        if not Logger.instance:
            Logger.instance = Logger.__Logger()

    def get_logger(self):
        return self.instance._logger


def tokenize_and_map(line, vocab):
    return [vocab.get(token, Config.data.UNK_ID) for token in line.split(' ')]


def make_input_fn(
        batch_size, input_filename, output_filename, vocab,
        input_max_length, output_max_length,
        input_process=tokenize_and_map, output_process=tokenize_and_map):

    def input_fn():
        inp = tf.placeholder(tf.int64, shape=[None, None], name='input')
        output = tf.placeholder(tf.int64, shape=[None, None], name='output')
        tf.identity(inp[0], 'input_0')
        tf.identity(output[0], 'output_0')
        return {
            'input': inp,
            'output': output,
        }, None

    def sampler():
        input_path = os.path.join(Config.data.PROCESSED_PATH, input_filename)
        output_path = os.path.join(Config.data.PROCESSED_PATH, output_filename)

        while True:
            with open(input_path) as finput:
                with open(output_path) as foutput:
                    for in_line in finput:
                        out_line = foutput.readline()
                        yield {
                            'input': input_process(in_line, vocab)[:input_max_length - 1] + [Config.data.EOS_ID],
                            'output': output_process(out_line, vocab)[:output_max_length - 1] + [Config.data.EOS_ID]
                        }

    sample_me = sampler()

    def feed_fn():
        inputs, outputs = [], []
        input_length, output_length = 0, 0
        for i in range(batch_size):
            rec = next(sample_me)
            inputs.append(rec['input'])
            outputs.append(rec['output'])
            input_length = max(input_length, len(inputs[-1]))
            output_length = max(output_length, len(outputs[-1]))
        # Pad me right with pad_id
        for i in range(batch_size):
            inputs[i] += [Config.data.PAD_ID] * (input_length - len(inputs[i]))
            outputs[i] += [Config.data.PAD_ID] * (output_length - len(outputs[i]))
        return {
            'input:0': inputs,
            'output:0': outputs
        }

    return input_fn, feed_fn


def load_vocab(filename):
    vocab = {}
    vocab_path = os.path.join(Config.data.PROCESSED_PATH, filename)
    with open(vocab_path) as f:
        for idx, line in enumerate(f):
            vocab[line.strip()] = idx
    return vocab


def get_rev_vocab(vocab):
    return {idx: key for key, idx in vocab.items()}


def get_formatter(keys, vocab):
    rev_vocab = get_rev_vocab(vocab)

    def to_str(sequence):
        tokens = [
            rev_vocab.get(x, "<unk>") for x in sequence]
        return ' '.join(tokens)

    def format(values):
        res = []
        for key in keys:
            res.append("%s = %s" % (key, to_str(values[key])))
        return '\n'.join(res)
    return format
