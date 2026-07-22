---
title: "Who actually sees your AI prompts?"
date: 2026-07-21
description: "You don't need a $30k server to keep your business data private when you use AI. You need to know who's in the request path. Here's the four-tier ladder I use, from 'they read everything by design' to 'nobody can see it, provably.'"
tags: [ai, privacy, ownership]
draft: false
---

A question I keep running into — and kept asking myself: if you don't have the hardware to run a serious AI model at home, can you rent someone else's and keep your data private?

The answer is yes. But "rented hardware" covers everything from *genuinely private* to *a company's software reads every word you send it*, and most people have no idea which one they're using.

Here's the test that cuts through all of it: **who's in the request path?** Not who *promises* what. Who actually touches your data on its way to the model.

## The four tiers

**Tier 1: An AI service's API.** This is what almost everybody uses — you send your prompt to a provider and their model answers. Understand what that means: your data arrives at their servers in plain text and runs through *their* software. They process every word **by design** — that's literally how the product works. "Zero data retention" agreements are real and worth having, but read what they actually say: *we promise not to store or train on it.* Not: *we can't see it.* Their code is the thing reading it. That's paperwork security, not architecture.

**Tier 2: Rented GPUs running your own model.** This is the tier most people don't know exists. You rent raw compute from a datacenter, install an open-weights model yourself, and point your tools at your own endpoint. Now there's no company in the request path — the model is just files on a machine you control, and traffic goes encrypted straight to your own software. What's left is the landlord risk: whoever owns the physical machine *could* go after your data, the same way a datacenter *could* image the disks of any server. But that's a deliberate attack, not a business process. Nobody sees anything unless they actively come after you. For business-confidential work, that's a completely different world than tier 1.

**Tier 3: Confidential computing.** The big clouds now rent machines where the memory — including the GPU's — is encrypted with keys the host never holds, and you can cryptographically *verify* the machine is in that state before you send a single byte. Even a subpoenaed operator gets scrambled noise from a memory dump. This is the only rented tier where "they can't see it" is a hardware guarantee instead of a promise. When a contract requires provable isolation — healthcare data, regulated industries — this is the tier the contract is asking for.

**Tier 4: Your own hardware.** Nobody. Full stop. The ceiling is whatever machine you can afford, which is exactly why the other tiers exist.

## The reality check on big models

Here's where people get burned: the headline open models are enormous. The current monsters need eight top-end GPUs just to wake up — renting that runs $30–60+ an hour. Demo money, not daily-driver money.

The move that gets you 90% of the value: run a strong open model that fits on **one** rented GPU at $2–4 an hour, spun up when you need it, torn down when you don't. Same privacy architecture, one-tenth the cost. The gap between the best open model and the best one-GPU open model is much smaller than the gap between "a company reads all my prompts" and "nobody does."

## How I actually run it

I don't pick one tier. I route by sensitivity:

- **Sensitive client data** → a model on hardware I own. Smaller model, zero third parties. This handles more of the boring work than you'd think.
- **Heavy but confidential** → rented dedicated GPU, my own model, reached over an encrypted tunnel, torn down after.
- **Everything else** → regular AI services, because for public-facing drafts and general questions, tier 1 is fine and it's the best-model-money-can-buy.

Notice the theme. It's the same one I bring to every system I build: **ownership**. When the model runs on infrastructure you control, your data privacy isn't a clause in someone's terms of service — it's a property of the architecture. Nobody can leak what they never saw.

If you're feeding client data into AI tools and you've never asked who's in the request path, that's worth an afternoon of your attention. And if you'd rather someone just build the routing for you — that's literally what I do.
