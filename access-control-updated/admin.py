from flask_admin.contrib.sqla import ModelView
from flask_admin import AdminIndexView, expose



class AdminView(ModelView):
    can_create=False
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.static_folder = 'static'



