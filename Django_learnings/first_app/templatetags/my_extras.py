from django import template

register=template.Library()

def cut2(text,args):
    '''
        cut all the passed arguments from string
    '''
    for arg in args:
        text=text.replace(arg,"")
    return text

register.filter('cut2',cut2)

@register.filter(name='cut3')
def cut3(text,args):
    '''
        cut all the passed arguments from string
    '''
    for arg in args:
        text=text.replace(arg,"")
    return text