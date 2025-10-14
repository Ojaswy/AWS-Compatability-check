# AWS-Compatability-check

1. Pull all the available instance data from all available regions (My account had access to 17 regions out of 38)
2. Group them by region - grouped_full_catalog.csv
3. Based on mutiple features like - Processor architecture, Supported virtualization types, EnaSupport, Ipv6Supported, MaximumNetworkInterfaces, NVMe support, InstanceStorageSupported (Boolean), Hypervisor, and BareMetal - build an interchangability matrix
4. From the interchangeable matrix - it suggests the best recommendation based on -  "current_instance_type", "required_vcpus", "required_memory_mib", "required_gpus"
 
[API Link](https://mdcmmla4nk.execute-api.us-west-2.amazonaws.com/dev)

Result for 

![](https://raw.githubusercontent.com/Ojaswy/AWS-Compatability-check/refs/heads/main/op_aws_api.png)

Resources: [Compatibility for changing the instance type](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/resize-limitations.html)

