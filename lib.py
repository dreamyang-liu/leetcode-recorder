import leetcode
import leetcode.auth
import json
import time
import datetime
from tqdm import tqdm
from constants import *
from notion_client import Client
from submissions import submission_parser

global_notion_client = None

global_leetcode_api_instance = None


def initialize_notion_client():
    global global_notion_client
    global_notion_client = Client(auth=NOTION_TOKEN)


def initialize_leetcode_api_instance():
    global global_leetcode_api_instance
    if global_leetcode_api_instance is not None:
        return
    CSRF_TOKEN = leetcode.auth.get_csrf_cookie(LEETCODE_SESSION)

    configuration = leetcode.Configuration()
    configuration.api_key["x-csrftoken"] = CSRF_TOKEN
    configuration.api_key["csrftoken"] = CSRF_TOKEN
    configuration.api_key["LEETCODE_SESSION"] = LEETCODE_SESSION
    configuration.api_key["Referer"] = "https://leetcode.com"
    configuration.debug = False

    global_leetcode_api_instance = leetcode.DefaultApi(
        leetcode.ApiClient(configuration)
    )


def get_leetcode_details(title_slug):
    graphql_request = leetcode.GraphqlQuery(
        query="""
        query getQuestionDetail($titleSlug: String!) {
                question(titleSlug: $titleSlug) {
                    title
                    titleSlug
                    difficulty
                    topicTags {
                    name
                    slug
                    }
                }
                }
        """,
        variables=leetcode.GraphqlQueryGetQuestionDetailVariables(
            title_slug=title_slug
        ),
        operation_name="getQuestionDetail",
    )
    return global_leetcode_api_instance.graphql_post(body=graphql_request)


def get_user_created_problem_list(list_id):
    qr = """
        query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
    problemsetQuestionList: questionList(
        categorySlug: $categorySlug
        limit: $limit
        skip: $skip
        filters: $filters
    ) {
        total: totalNum
        questions: data {
        acRate
        difficulty
        freqBar
        frontendQuestionId: questionFrontendId
        isFavor
        paidOnly: isPaidOnly
        status
        title
        titleSlug
        topicTags {
            name
            id
            slug
        }
        hasSolution
        hasVideoSolution
        }
    }
    }
    """
    query = leetcode.GraphqlQuery(
        query=qr,
        variables=leetcode.GraphqlQueryProblemsetQuestionListVariables(
            category_slug="all-code-essentials",
            filters={"listId": list_id},
            limit=1000,
        ),
        operation_name="problemsetQuestionList",
    )
    return global_leetcode_api_instance.graphql_post(body=query)


def create_leetcode_problem_database_entry(
    database_id, title, link, topics, difficulty
):
    global_notion_client.pages.create(
        **{
            "parent": {"type": "database_id", "database_id": database_id},
            "properties": {
                "Question Name": {
                    "type": "title",
                    "title": [{"text": {"content": title}}],
                },
                "Link": {"type": "url", "url": link},
                "Topics": {
                    "type": "multi_select",
                    "multi_select": [{"name": topic} for topic in topics],
                },
                "Difficulty": {"type": "select", "select": {"name": difficulty}},
            },
        }
    )


def get_page_id_by_title_within_database(database_id, title):
    pages_results = global_notion_client.databases.query(database_id=database_id)
    pages = []
    while pages_results["has_more"]:
        pages += pages_results["results"]
        pages_results = global_notion_client.databases.query(
            database_id=database_id, start_cursor=pages_results["next_cursor"]
        )
    pages += pages_results["results"]
    for page in pages:
        if (
            page["properties"]["Question Name"]["title"]
            and page["properties"]["Question Name"]["title"][0]["plain_text"] == title
        ):
            return page["id"]
    return None


def update_problem_with_lastest_submission(
    database_id: str,
    title: str,
    timestamp: str,
    title_slug: str,
    has_complexity: bool = None,
    has_two_or_more_solutions: bool = None,
    thinkging_time: int = None,
    coding_time: int = None,
    use_hint: bool = None,
    use_solution: bool = None,
    eliminate_3_lines: bool = None,
):
    try:
        if (
            get_page_id_by_title_within_database(database_id=database_id, title=title)
            is None
        ):
            problem_detail = get_leetcode_details(title_slug)
            create_leetcode_problem_database_entry(
                database_id,
                title,
                LEETCODE_PROBLEM_BASE_URL + title_slug,
                [
                    topic["name"]
                    for topic in problem_detail.to_dict()["data"]["question"][
                        "topic_tags"
                    ]
                ],
                problem_detail.to_dict()["data"]["question"]["difficulty"],
            )
        properties = {}
        properties["Recent submit date"] = {
            "type": "date",
            "date": {"start": datetime.datetime.fromtimestamp(timestamp).isoformat()},
        }
        properties["Pass all test cases"] = {
            "type": "checkbox",
            "checkbox": True,
        }
        if has_complexity is not None:
            properties["Time / Space complexity"] = {
                "type": "checkbox",
                "checkbox": has_complexity,
            }
        if has_two_or_more_solutions:
            properties["Two methods"] = {
                "type": "checkbox",
                "checkbox": has_two_or_more_solutions,
            }
        if thinkging_time is not None:
            properties["Thinking Elapsed"] = {
                "type": "number",
                "number": thinkging_time,
            }
        if coding_time is not None:
            properties["Coding Elapsed"] = {
                "type": "number",
                "number": coding_time,
            }
        if use_hint is not None:
            properties["Use Hint"] = {"type": "checkbox", "checkbox": use_hint}
        if use_solution is not None:
            properties["Use Solution"] = {"type": "checkbox", "checkbox": use_solution}
        if eliminate_3_lines is not None:
            properties["Eliminate 3 lines"] = {
                "type": "checkbox",
                "checkbox": eliminate_3_lines,
            }
        global_notion_client.pages.update(
            **{
                "page_id": get_page_id_by_title_within_database(
                    database_id=database_id, title=title
                ),
                "properties": {**properties},
            }
        )
    except Exception as e:
        print(title, e)


def add_or_update_leetcode_problem_entry(database_id, title, link, topics, difficulty):
    page_id = get_page_id_by_title_within_database(database_id, title)
    if page_id is None:
        global_notion_client.pages.create(
            **{
                "parent": {"type": "database_id", "database_id": database_id},
                "properties": {
                    "Question Name": {
                        "type": "title",
                        "title": [{"text": {"content": title}}],
                    },
                    "Link": {"type": "url", "url": link},
                    "Topics": {
                        "type": "multi_select",
                        "multi_select": [{"name": topic} for topic in topics],
                    },
                    "Difficulty": {"type": "select", "select": {"name": difficulty}},
                },
            }
        )
    else:
        global_notion_client.pages.update(
            **{
                "page_id": get_page_id_by_title_within_database(
                    database_id=database_id, title=title
                ),
                "properties": {
                    "Question Name": {
                        "type": "title",
                        "title": [{"text": {"content": title}}],
                    },
                    "Link": {"type": "url", "url": link},
                    "Topics": {
                        "type": "multi_select",
                        "multi_select": [{"name": topic} for topic in topics],
                    },
                    "Difficulty": {"type": "select", "select": {"name": difficulty}},
                },
            }
        )


def delete_leetcode_problem_entry(database_id, title):
    global_notion_client.pages.update(
        **{
            "page_id": get_page_id_by_title_within_database(database_id, title),
            "archived": True,
        }
    )


def add_custom_list_to_database(database_id):
    for question in get_user_created_problem_list().to_dict()["data"][
        "problemset_question_list"
    ]["questions"]:
        add_or_update_leetcode_problem_entry(
            database_id,
            question["title"],
            LEETCODE_PROBLEM_BASE_URL + question["title_slug"],
            [topic["name"] for topic in question["topic_tags"]],
            question["difficulty"],
        )


def add_company_or_topic_list_to_notion(database_id, topic_slug="dynamic-programming"):
    questions = json.loads(
        global_leetcode_api_instance.api_client.request(
            "GET", f"https://leetcode.com/problems/tag-data/question-tags/{topic_slug}/"
        ).data
    )["questions"]
    for question in tqdm(questions):
        add_or_update_leetcode_problem_entry(
            database_id,
            question["title"],
            LEETCODE_PROBLEM_BASE_URL + question["titleSlug"],
            [topic["name"] for topic in question["topicTags"]],
            question["difficulty"],
        )


def get_last_n_leetcode_submission_and_update_notion(database_id, n):
    submissions = []
    for offset in range(0, n + 1, 20):
        time.sleep(2)
        submissions += json.loads(
            global_leetcode_api_instance.api_get_submissions_with_http_info(
                offset=offset
            ).data.decode("utf-8")
        )["submissions_dump"]
    submission_list = []
    visited_problem = set()
    for submission in submissions:
        if submission["status_display"] == "Accepted":
            if submission["title"] not in visited_problem:
                visited_problem.add(submission["title"])
                submission_list.append(submission_parser(submission))
    for has_metadata, submission in tqdm(submission_list):
        if has_metadata:
            update_problem_with_lastest_submission(
                database_id,
                title=submission["title"],
                timestamp=submission["timestamp"],
                title_slug=submission["title_slug"],
                has_complexity=submission["has_complexity"],
                has_two_or_more_solutions=submission["has_two_or_more_solutions"],
                thinkging_time=submission["thinkging_time"],
                coding_time=submission["coding_time"],
                use_hint=submission["use_hint"],
                use_solution=submission["use_solution"],
                eliminate_3_lines=submission["eliminate_3_lines"],
            )
        else:
            update_problem_with_lastest_submission(
                database_id,
                title=submission["title"],
                timestamp=submission["timestamp"],
                title_slug=submission["title_slug"],
            )


initialize_leetcode_api_instance()
initialize_notion_client()
