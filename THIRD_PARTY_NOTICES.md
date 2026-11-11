# Third-party software and license notices

This repository is a guide and reference implementation. It does not include upstream Xray Core or 3x-ui source trees or compiled binaries. The setup instructions download and build those projects separately on the operator's own server.

The MIT License in this repository applies only to the original files provided here, unless an individual file contains a different notice. It does not relicense third-party software or override their license terms.

| Project | Upstream license notice | Project website |
|---|---|---|
| Xray Core | Mozilla Public License 2.0 (MPL-2.0) | <https://github.com/XTLS/Xray-core> |
| 3x-ui | GNU General Public License v3.0 (GPL-3.0) | <https://github.com/MHSanaei/3x-ui> |
| Tailscale | See current product and source licensing terms | <https://tailscale.com/> |
| Python, Go, FastAPI, Uvicorn, and other dependencies | Each project retains its own license | Consult the relevant upstream project and package metadata |

The Xray patch helper in this repository is intended to modify a separate Xray Core source checkout. When users apply the patch, the resulting modified Xray Core source remains subject to Xray Core's applicable license. Review the upstream license and notices before redistributing modified Xray source or binaries.

License identifiers and upstream terms can change. Always check the license files shipped with the exact versions you download. This notice is informational and is not legal advice.
