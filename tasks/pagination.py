from rest_framework.pagination import PageNumberPagination
# the number of tasks that will be displayed per page is 10, but the user can change it by adding a query parameter to the url. for example, if the user wants to see 20 tasks per page, he can add ?page_size=20 to the url. and the maximum number of tasks that can be displayed per page is 100.
# all of this to prevent the user from requesting too many tasks at once and crashing the server.
class TaskPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100
