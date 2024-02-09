from argparse import ArgumentParser
from constants import *
from lib import *

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--update_with_submission", action="store_true")
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--import_tag", action="store_true")
    parser.add_argument("--tag", type=str, default="array")
    parser.add_argument("--database_id", type=str, default=DATABASE_ID)

    args = parser.parse_args()
    if args.update_with_submission:
        get_last_n_leetcode_submission_and_update_notion(args.database_id, args.n)
    if args.import_tag:
        add_company_or_topic_list_to_notion(args.database_id, args.tag)
