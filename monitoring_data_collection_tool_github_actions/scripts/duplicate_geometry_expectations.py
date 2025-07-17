import pandas as pd
import ast
import argparse
import os

def parse_args():
    parser = argparse.ArgumentParser(description="Duplicate geometry checker")
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Directory to save exported CSVs"
    )
    return parser.parse_args()

def parse_details(val):
    try:
        return ast.literal_eval(val)
    except Exception:
        return {}

def extract_stats(details_dict):
    return pd.Series({
        "actual": details_dict.get("actual"),
        "expected": details_dict.get("expected"),
        "complete_match_count": len(details_dict.get("complete_matches", [])) if isinstance(details_dict.get("complete_matches"), list) else 0,
        "single_match_count": len(details_dict.get("single_matches", [])) if isinstance(details_dict.get("single_matches"), list) else 0,
        "complete_matches": details_dict.get("complete_matches", []),
        "single_matches": details_dict.get("single_matches", [])
    })

def main(output_dir):
    # Load expectation records
    url = "https://datasette.planning.data.gov.uk/digital-land/expectation.csv?_stream=on"
    df = pd.read_csv(url)
    df = df[df["operation"] == "duplicate_geometry_check"].copy()
    df["details_parsed"] = df["details"].apply(parse_details)

    # Extract matches
    records = []
    for _, row in df.iterrows():
        dataset = row["dataset"]
        operation = row["operation"]
        details = row["details_parsed"]
        for match in details.get("complete_matches", []):
            records.append({
                "dataset": dataset,
                "operation": operation,
                "message": "complete_match",
                "entity_a": match.get("entity_a"),
                "organisation_entity_a": match.get("organisation_entity_a"),
                "entity_b": match.get("entity_b"),
                "organisation_entity_b": match.get("organisation_entity_b"),
            })
        for match in details.get("single_matches", []):
            records.append({
                "dataset": dataset,
                "operation": operation,
                "message": "single_match",
                "entity_a": match.get("entity_a"),
                "organisation_entity_a": match.get("organisation_entity_a"),
                "entity_b": match.get("entity_b"),
                "organisation_entity_b": match.get("organisation_entity_b"),
            })
    df_matches = pd.DataFrame(records)

    # Entity URLs and columns
    url_map = {
        "conservation-area": "https://datasette.planning.data.gov.uk/conservation-area/entity.csv?_stream=on",
        "article-4-direction-area": "https://datasette.planning.data.gov.uk/article-4-direction-area/entity.csv?_stream=on",
        "listed-building-outline": "https://datasette.planning.data.gov.uk/listed-building-outline/entity.csv?_stream=on",
        "tree-preservation-zone": "https://datasette.planning.data.gov.uk/tree-preservation-zone/entity.csv?_stream=on",
        "tree": "https://datasette.planning.data.gov.uk/tree/entity.csv?_stream=on",
    }
    columns_to_keep = ["entity", "dataset", "end_date", "entry_date", "geometry", "name", "organisation_entity"]
    entity_tables = {}
    for dataset_name, entity_url in url_map.items():
        df_entity = pd.read_csv(entity_url)
        df_entity["dataset"] = dataset_name
        entity_tables[dataset_name] = df_entity[columns_to_keep].copy()
    df_entities = pd.concat(entity_tables.values(), ignore_index=True)

    # Merge entity metadata
    df_matches = df_matches.merge(
        df_entities,
        how="left",
        left_on=["dataset", "entity_a"],
        right_on=["dataset", "entity"]
    ).rename(columns={
        "end_date": "entity_a_end_date",
        "entry_date": "entity_a_entry_date",
        "geometry": "entity_a_geometry",
        "name": "entity_a_name",
        "organisation_entity": "entity_a_organisation"
    }).drop(columns=["entity"])

    df_matches = df_matches.merge(
        df_entities,
        how="left",
        left_on=["dataset", "entity_b"],
        right_on=["dataset", "entity"]
    ).rename(columns={
        "end_date": "entity_b_end_date",
        "entry_date": "entity_b_entry_date",
        "geometry": "entity_b_geometry",
        "name": "entity_b_name",
        "organisation_entity": "entity_b_organisation"
    }).drop(columns=["entity"])

    # Load organisation names
    org_url = "https://datasette.planning.data.gov.uk/digital-land/organisation.csv?_stream=on"
    df_org = pd.read_csv(org_url)[["entity", "name"]].rename(columns={
        "entity": "organisation_entity",
        "name": "organisation_name"
    })

    df_matches = df_matches.merge(
        df_org,
        how="left",
        left_on="entity_a_organisation",
        right_on="organisation_entity"
    ).rename(columns={"organisation_name": "entity_a_organisation_name"}).drop(columns=["organisation_entity"])

    a_cols = df_matches.columns.tolist()
    a_index = a_cols.index("entity_a_organisation") + 1
    a_cols.insert(a_index, a_cols.pop(a_cols.index("entity_a_organisation_name")))
    df_matches = df_matches[a_cols]

    df_matches = df_matches.merge(
        df_org,
        how="left",
        left_on="entity_b_organisation",
        right_on="organisation_entity"
    ).rename(columns={"organisation_name": "entity_b_organisation_name"}).drop(columns=["organisation_entity"])

    b_cols = df_matches.columns.tolist()
    b_index = b_cols.index("entity_b_organisation") + 1
    b_cols.insert(b_index, b_cols.pop(b_cols.index("entity_b_organisation_name")))
    df_matches = df_matches[b_cols]

    # --- Endpoint mapping ---
    # --- Endpoint mapping (deduplicated per organisation) ---
    endpoint_url = "https://datasette.planning.data.gov.uk/digital-land/endpoint.csv?_stream=on"
    df0 = pd.read_csv(endpoint_url)
    df0 = df0[df0['end_date'].isna()]
    df_endpoint = df0[["endpoint", "endpoint_url"]].copy()

    source_url = "https://datasette.planning.data.gov.uk/digital-land/source.csv?_stream=on"
    df1 = pd.read_csv(source_url)
    df1["organisation_ref"] = df1["organisation"].str.replace(r"^.*?:", "", regex=True).astype(str)
    df_source = df1[["endpoint", "source", "collection", "organisation_ref"]].copy()

    df2 = pd.read_csv(org_url)
    df2 = df2[df2['end_date'].isna()]
    df2["reference"] = df2["reference"].astype(str)
    df_org_ep = df2[["name", "reference"]].rename(columns={"name": "organisation", "reference": "organisation_ref"})

    # Merge and keep only one endpoint per organisation (first occurrence)
    df_ep_org = df_endpoint.merge(df_source, on="endpoint", how="left")
    df_ep_org = df_ep_org.merge(df_org_ep, on="organisation_ref", how="left")
    df_ep_org = df_ep_org[["endpoint", "organisation"]].dropna()
    df_ep_org = df_ep_org.drop_duplicates(subset=["organisation"])  # This line prevents row explosion

    # Add entity_a_endpoint (safe one-to-one)
    df_matches = df_matches.merge(
        df_ep_org.rename(columns={"endpoint": "entity_a_endpoint", "organisation": "entity_a_organisation_name"}),
        on="entity_a_organisation_name",
        how="left"
    )

    # Add entity_b_endpoint (safe one-to-one)
    df_matches = df_matches.merge(
        df_ep_org.rename(columns={"endpoint": "entity_b_endpoint", "organisation": "entity_b_organisation_name"}),
        on="entity_b_organisation_name",
        how="left"
    )
    
    # Reorder columns
    cols = df_matches.columns.tolist()
    a_ep_index = cols.index("entity_a_organisation_name") + 1
    cols.insert(a_ep_index, cols.pop(cols.index("entity_a_endpoint")))
    b_ep_index = cols.index("entity_b_organisation_name") + 1
    cols.insert(b_ep_index, cols.pop(cols.index("entity_b_endpoint")))
    df_matches = df_matches[cols]

    # Drop rows where both endpoints are the same
    df_matches = df_matches[df_matches["entity_a_endpoint"] != df_matches["entity_b_endpoint"]]

    # Save CSVs
    os.makedirs(output_dir, exist_ok=True)
    matches_csv = os.path.join(output_dir, "duplicate_entity_expectation.csv")
    df_matches.to_csv(matches_csv, index=False)

    stats_df = pd.concat([df[["dataset", "severity"]], df["details_parsed"].apply(extract_stats)], axis=1)
    stats_df = stats_df.sort_values(by="complete_match_count", ascending=False).reset_index(drop=True)
    summary_csv = os.path.join(output_dir, "duplicate_entity_expectation_summary.csv")
    stats_df.drop(columns=["complete_matches", "single_matches"]).to_csv(summary_csv, index=False)

# Entry point
if __name__ == "__main__":
    args = parse_args()
    main(args.output_dir)
