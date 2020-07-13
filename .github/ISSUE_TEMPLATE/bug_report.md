---
name: Bug report
about: 'Report a problem or unexpected failure '
title: ''
labels: bug
assignees: jynik

---

**Describe the bug**

Please describe the failure or problem you're experiencing. 

**Depthcharge Version**

What version of the Depthcharge codebase are you using? If between releases, please specify the exact git commit.

**Target System**

If the issue requires a specific target U-Boot version or hardware platform, please list these here.

If we cannot reproduce the issue without a specific piece of target hardware, bear in mind that we may not be able to resolve the issue quickly.

**Logs**

Please provide the following log files. If these contain sensitive information, please redact this or otherwise reach out to us for a secure exchange of these files.

1. Depthcharge log output written to stderr. Please record this with the `DEPTHCHARGE_LOG_LEVEL` environment variable set to `debug`.
1. A Console log, as recorded by `depthcharge.monitor.FileMonitor`. For command line tools, this can be recorded via a `-m file:console.log` argument.



**Screenshots**

If applicable, add screenshots to help explain your problem.

**Additional context**
Add any other context about the problem here.
