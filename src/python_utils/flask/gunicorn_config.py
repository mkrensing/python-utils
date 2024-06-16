from python_utils.flask.shared import init_global_data_share, destroy_global_data_share

def on_starting(server):
    print("gunicorn.onstarting")
    init_global_data_share()

def on_exit(server):
    print("gunicorn.on_exit")
    destroy_global_data_share()