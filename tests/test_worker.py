import json
from multiprocessing import Queue
from Queue import Empty

import boto
from boto.sqs.message import Message
from moto import mock_sqs
import sure  # flake8: noqa

from pyqs.worker import ReadWorker, ProcessWorker
from tests.tasks import task_results


@mock_sqs
def test_worker_fills_internal_queue():
    conn = boto.connect_sqs()
    queue = conn.create_queue("tester")

    message = Message()
    body = json.dumps({
        'task': 'tests.tasks.index_incrementer',
        'args': [],
        'kwargs': {
            'message': 'Test message',
        },
    })
    message.set_body(body)
    queue.write(message)

    internal_queue = Queue()
    worker = ReadWorker(queue, internal_queue)
    worker.read_message()

    found_message = internal_queue.get(timeout=1)

    found_message.should.equal({
        'task': 'tests.tasks.index_incrementer',
        'args': [],
        'kwargs': {
            'message': 'Test message',
        },
    })


@mock_sqs
def test_worker_fills_internal_queue_from_celery_task():
    conn = boto.connect_sqs()
    queue = conn.create_queue("tester")

    message = Message()
    body = '{"body": "KGRwMApTJ3Rhc2snCnAxClMndGVzdHMudGFza3MuaW5kZXhfaW5jcmVtZW50ZXInCnAyCnNTJ2Fy\\nZ3MnCnAzCihscDQKc1Mna3dhcmdzJwpwNQooZHA2ClMnbWVzc2FnZScKcDcKUydUZXN0IG1lc3Nh\\nZ2UyJwpwOApzcy4=\\n", "some stuff": "asdfasf"}'
    message.set_body(body)
    queue.write(message)

    internal_queue = Queue()
    worker = ReadWorker(queue, internal_queue)
    worker.read_message()

    found_message = internal_queue.get(timeout=1)

    found_message.should.equal({
        'task': 'tests.tasks.index_incrementer',
        'args': [],
        'kwargs': {
            'message': 'Test message2',
        },
    })


def test_worker_processes_tasks_from_internal_queue():
    message = {
        'task': 'tests.tasks.index_incrementer',
        'args': [],
        'kwargs': {
            'message': 'Test message',
        },
    }
    internal_queue = Queue()
    internal_queue.put(message)

    worker = ProcessWorker(internal_queue)
    worker.process_message()

    task_results.should.equal(['Test message'])

    try:
        internal_queue.get(timeout=1)
    except Empty:
        pass
    else:
        raise AssertionError("The internal queue should be empty")


def test_worker_processes_empty_queue():
    internal_queue = Queue()

    worker = ProcessWorker(internal_queue)
    worker.process_message()
