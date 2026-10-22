from django.core.paginator import Paginator
from django.shortcuts import render


def render_page(request, template, key, queryset, context=None):
    page = Paginator(queryset.order_by('-pk'), 24).get_page(request.GET.get('page'))
    query = request.GET.copy()
    query.pop('page', None)
    return render(request, template, {**(context or {}), key: page, 'page_obj': page, 'page_query': query.urlencode()})
