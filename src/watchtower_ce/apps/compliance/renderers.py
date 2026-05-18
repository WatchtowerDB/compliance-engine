from rest_framework.renderers import BaseRenderer


class SSERenderer(BaseRenderer):
    media_type = "text/event-stream"
    format = "txt"  # if it doesn't work, try 'sse'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data
