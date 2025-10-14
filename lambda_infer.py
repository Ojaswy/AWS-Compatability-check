import os
import json
import math
import boto3
import pandas as pd

s3 = boto3.client("s3")

# ---------------------------
# Load CSV from S3
# ---------------------------
def load_df_from_s3(bucket, key):
    obj = s3.get_object(Bucket=bucket, Key=key)
    return pd.read_csv(obj['Body'])


# ---------------------------
# Recommendation logic
# ---------------------------
def recommend_instance(current_instance_type, required_vcpus, required_memory_mib, required_gpus,
                       instances_df, matrix_df, top_n=3):

    # Ensure index/columns are strings
    matrix_df.index = matrix_df.index.astype(str)
    matrix_df.columns = matrix_df.columns.astype(str)

    # Build map InstanceType -> row dict
    name_map = instances_df.set_index('InstanceType').to_dict(orient='index')

    if current_instance_type not in name_map:
        raise ValueError(f"Current instance {current_instance_type} not found in catalog.")

    if current_instance_type not in matrix_df.index:
        raise ValueError(f"{current_instance_type} not found in interchangeability matrix index.")

    # Get interchangeable targets (directional: targets that can replace the source)
    interchangeable_series = matrix_df.loc[current_instance_type]
    compatible_names = [
        str(name) for name, ok in interchangeable_series.items() 
        if bool(ok) and str(name) != current_instance_type
    ]

    if not compatible_names:
        return {"error": f"No interchangeable instances found for {current_instance_type}."}

    # Evaluate candidates
    candidates = []
    for target in compatible_names:
        inst = name_map.get(target)
        if not inst:
            continue
        vcpu = int(inst.get("vCPUs", 0))
        mem = int(inst.get("MemoryMiB", 0))
        gpu = int(inst.get("GPUs", 0))

        if vcpu < required_vcpus or mem < required_memory_mib or gpu < required_gpus:
            continue

        # Distance metric
        mem_scaled = mem / 1024.0
        req_mem_scaled = required_memory_mib / 1024.0
        dist = math.sqrt((vcpu - required_vcpus)**2 + (mem_scaled - req_mem_scaled)**2 + (gpu - required_gpus)**2)

        candidates.append({
            "InstanceType": target,
            "vCPUs": vcpu,
            "MemoryMiB": mem,
            "GPUs": gpu,
            "Score": dist
        })

    if not candidates:
        return {"error": f"No compatible instance meets requirements (vCPU≥{required_vcpus}, Mem≥{required_memory_mib} MiB, GPU≥{required_gpus})."}

    candidates.sort(key=lambda x: x["Score"])
    best = candidates[0]
    top = candidates[:top_n]

    return {
        "current": current_instance_type,
        "requested": {"vcpus": required_vcpus, "memory_mib": required_memory_mib, "gpus": required_gpus},
        "best": best,
        "top_n": top
    }


# ---------------------------
# Lambda handler
# ---------------------------
def lambda_handler(event, context):
    try:
        # parse inputs
        current_instance_type = event.get("current_instance_type") or event.get("instance_type")
        required_vcpus = int(event.get("required_vcpus", 0))
        required_memory_mib = int(event.get("required_memory_mib", 0))
        required_gpus = int(event.get("required_gpus", 0))
        top_n = int(event.get("top_n", 3))

        # S3 locations
        bucket = event.get("bucket")
        catalog_key = event.get("catalog_key")
        matrix_key = event.get("matrix_key")

        if not bucket or not catalog_key or not matrix_key:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing S3 bucket, catalog_key, or matrix_key."})}

        # Load CSVs
        catalog_df = load_df_from_s3(bucket, catalog_key)
        matrix_df = load_df_from_s3(bucket, matrix_key)

        # Convert matrix to boolean (just in case)
        matrix_df = matrix_df.set_index(matrix_df.columns[0])
        matrix_df = matrix_df.applymap(lambda x: bool(x))

        # Run recommendation
        result = recommend_instance(
            current_instance_type,
            required_vcpus,
            required_memory_mib,
            required_gpus,
            catalog_df,
            matrix_df,
            top_n=top_n
        )

        return {"statusCode": 200, "body": json.dumps(result)}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
