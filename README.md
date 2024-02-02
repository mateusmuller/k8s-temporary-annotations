# k8s-temporary-annotations  - Simple tool to add and remove temporary annotations to pods

# Introduction

k8s-temporary-annotations adds annotations to your Kubernetes pods through a Mutating Webhook, and removes later on with a scheduled function.


# Why?

This is a personal project to practice Python.

At the same time I would like to do something useful. The use case for this tool is described [here](https://github.com/kubernetes-sigs/karpenter/issues/735).

Basically I'd like to inject a "non disruption" to avoid pod deletion during a time range. But I need to get the 
metadata removed later on.

# How to use?

TBD