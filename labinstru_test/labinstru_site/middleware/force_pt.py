from django.utils import translation

class ForcePortugueseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        translation.activate('pt-br')
        request.LANGUAGE_CODE = 'pt-br'
        response = self.get_response(request)
        translation.deactivate()
        return response
