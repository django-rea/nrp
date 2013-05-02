from decimal import *
from django.forms.widgets import MultiWidget, TextInput

class DurationWidget(MultiWidget):
    def __init__(self, attrs=None):
        _widgets = (
            TextInput(attrs={"class": "days",}),
            TextInput(attrs={"class": "hours",}),
            TextInput(attrs={"class": "minutes",}),
        )
        super(DurationWidget, self).__init__(_widgets, attrs)

    def decompress(self, value):
        #import pdb; pdb.set_trace()
        if value:
            duration = int(value)
            days = duration / 1440
            hours = (duration - (days * 1440)) / 60
            minutes = duration - (days * 1440) - (hours * 60)
            return [days, hours, minutes]
        return [0, 0, 0]

    def format_output(self, rendered_widgets):
        return u''.join(rendered_widgets)

    def value_from_datadict(self, data, files, name):
        #import pdb; pdb.set_trace()
        dlist = [
            widget.value_from_datadict(data, files, name + '_%s' % i)
            for i, widget in enumerate(self.widgets)]
        #make more forgiving: change '' to 0
        try:
            days = int(dlist[0])
        except ValueError:
            days = 0
        try:
            hours = int(dlist[1])
        except ValueError:
            hours = 0
        try:
            mins = int(dlist[2])
        except ValueError:
            mins = 0
        try:
            duration = ((days * 1440) + (hours * 60) + mins)
        except ValueError:
            return 0
        else:
            return duration


class DecimalDurationWidget(MultiWidget):
    #todo: this widget assumes decimal hours
    # but that assumes too much
    # unit_of_quantity cd be any unit of time
    # how to resolve?
    def __init__(self, attrs=None):
        _widgets = (
            TextInput(attrs={"class": "hours",}),
            TextInput(attrs={"class": "minutes",}),
        )
        super(DecimalDurationWidget, self).__init__(_widgets, attrs)

    def decompress(self, value):
        #import pdb; pdb.set_trace()
        if value:
            duration = int(value)
            #days = duration / 24
            #hours = duration - (days * 24)
            hours = duration
            mins = value - duration
            minutes = int((60 * mins).quantize(Decimal('1'), rounding=ROUND_UP))
            return [hours, minutes]
        return [0, 0]

    def format_output(self, rendered_widgets):
        return u''.join(rendered_widgets)

    def value_from_datadict(self, data, files, name):
        #import pdb; pdb.set_trace()
        dlist = [
            widget.value_from_datadict(data, files, name + '_%s' % i)
            for i, widget in enumerate(self.widgets)]
        #make more forgiving: change '' to 0
        try:
            hours = int(dlist[0])
        except ValueError:
            hours = 0
        try:
            mins = int(dlist[1])
        except ValueError:
            mins = 0
        #import pdb; pdb.set_trace()
        try:
            duration = Decimal(hours)
            duration += Decimal(mins) / 60
        except ValueError:
            return Decimal("0")
        else:
            return duration

    def _has_changed(self, initial, data):
        #import pdb; pdb.set_trace()
        if initial is None:
            initial = [u'' for x in range(0, 2)]
        else:
            if not isinstance(initial, list):
                initial = self.decompress(initial)
        dlist = self.decompress(data)
        for widget, initial, data in zip(self.widgets, initial, dlist):
            if widget._has_changed(initial, data):
                return True
        return False
        
class DecimalDurationWidgetOld(MultiWidget):
    #todo: this widget assumes decimal hours
    # but that assumes too much
    # unit_of_quantity cd be any unit of time
    # how to resolve?
    def __init__(self, attrs=None):
        _widgets = (
            TextInput(attrs={"class": "days",}),
            TextInput(attrs={"class": "hours",}),
            TextInput(attrs={"class": "minutes",}),
        )
        super(DecimalDurationWidget, self).__init__(_widgets, attrs)

    def decompress(self, value):
        #import pdb; pdb.set_trace()
        if value:
            duration = int(value)
            days = duration / 24
            hours = duration - (days * 24)
            mins = value - duration
            minutes = int((60 * mins).quantize(Decimal('1'), rounding=ROUND_UP))
            return [days, hours, minutes]
        return [0, 0, 0]

    def format_output(self, rendered_widgets):
        return u''.join(rendered_widgets)

    def value_from_datadict(self, data, files, name):
        #import pdb; pdb.set_trace()
        dlist = [
            widget.value_from_datadict(data, files, name + '_%s' % i)
            for i, widget in enumerate(self.widgets)]
        #make more forgiving: change '' to 0
        try:
            days = int(dlist[0])
        except ValueError:
            days = 0
        try:
            hours = int(dlist[1])
        except ValueError:
            hours = 0
        try:
            mins = int(dlist[2])
        except ValueError:
            mins = 0
        #import pdb; pdb.set_trace()
        try:
            duration = Decimal((days * 24) + hours)
            duration += Decimal(mins) / 60
        except ValueError:
            return Decimal("0")
        else:
            return duration

    def _has_changed(self, initial, data):
        #import pdb; pdb.set_trace()
        if initial is None:
            initial = [u'' for x in range(0, 3)]
        else:
            if not isinstance(initial, list):
                initial = self.decompress(initial)
        dlist = self.decompress(data)
        for widget, initial, data in zip(self.widgets, initial, dlist):
            if widget._has_changed(initial, data):
                return True
        return False
