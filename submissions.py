import json


def submission_parser(submission):
    metadata = {}
    metadata["title"] = submission["title"]
    metadata["timestamp"] = submission["timestamp"]
    metadata["title_slug"] = submission["title_slug"]
    try:
        print(submission["code"].split("'''")[1].strip())
        metadata["solutions"] = json.loads(submission["code"].split("'''")[1].strip())
        if (
            metadata["solutions"][0]["Time Complexity"]
            and metadata["solutions"][0]["Space Complexity"]
        ):
            metadata["has_complexity"] = True
        metadata["has_two_or_more_solutions"] = len(metadata["solutions"]) >= 2
        metadata["thinkging_time"] = round(sum(metadata["solutions"][i]["Thinking Time"] for i in range(len(metadata["solutions"]))) / len(metadata["solutions"]), 1)
        metadata["coding_time"] = round(sum(metadata["solutions"][i]["Coding Time"] for i in range(len(metadata["solutions"]))) / len(metadata["solutions"]), 1)
        metadata["use_hint"] = metadata["solutions"][0]["Use Hint"]
        metadata["use_solution"] = metadata["solutions"][0]["Use Solution"]
        if "Eliminate 3 Lines" in metadata["solutions"][0]:
            metadata["eliminate_3_lines"] = metadata["solutions"][0]["Eliminate 3 Lines"]
        else:
            metadata["eliminate_3_lines"] = False
        return True, metadata
    except Exception as e:
        print(f"Cannot parse metadata in submission {e}")
        return False, metadata
