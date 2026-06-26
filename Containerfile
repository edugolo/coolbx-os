# Coolbx OS — bootc image
# De concrete base is een open keuze (ADR-0004): bouw met --build-arg BASE_IMAGE=...
# Standaard = kaal fedora-bootc; de base-spike (S1) bouwt ook ghcr.io/ublue-os/base-main:43.
ARG BASE_IMAGE=quay.io/fedora/fedora-bootc:43

# Build-context als aparte stage zodat build_files/features niet in het eindbeeld landen.
FROM scratch AS ctx
COPY build_files /build_files
COPY features /features

FROM ${BASE_IMAGE}

ARG SHA_HEAD_SHORT=local
ARG IMAGE_VERSION=latest
# Veilige default: prod (géén dev-user/autologin). De dev-VM gebruikt `just build-dev` (=1).
ARG ENABLE_FIRSTBOOT_USER=0
# Spatie-gescheiden lijst van optionele features (bv. "kiosk focus branding"). Leeg = kale OS.
ARG FEATURES=""

LABEL org.opencontainers.image.title="Coolbx OS" \
      org.opencontainers.image.description="Vergrendelde Fedora bootc device-floor voor scholen" \
      org.opencontainers.image.vendor="coolbx" \
      org.opencontainers.image.version="${IMAGE_VERSION}" \
      org.opencontainers.image.revision="${SHA_HEAD_SHORT}" \
      containers.bootc="1"

# 1) Zware, cachebare pakket-laag
RUN --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=cache,dst=/var/cache \
    --mount=type=tmpfs,dst=/tmp \
    /ctx/build_files/01-packages.sh

# 2) System-files na de zware install (zodat de pakket-laag gecached blijft bij tweaks)
COPY system_files /

# 3) Lichte config (units enablen, locale, first-boot dev-user)
RUN --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=cache,dst=/var/cache \
    --mount=type=tmpfs,dst=/tmp \
    ENABLE_FIRSTBOOT_USER=${ENABLE_FIRSTBOOT_USER} /ctx/build_files/02-config.sh

# 4) GNOME-defaults (dconf/schemas)
RUN --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=tmpfs,dst=/tmp \
    /ctx/build_files/03-gnome-dconf.sh

# 5) Optionele features (modulair — ADR-0012)
# FEATURES_CACHEBUST: een --mount=type=bind invalideert de laag NIET bij gewijzigde
# bestandsinhoud (alleen het commando telt). Daarom busten de build-recepten deze laag
# expliciet met een wisselende waarde, zodat feature-edits altijd doorkomen.
ARG FEATURES_CACHEBUST=""
RUN --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=cache,dst=/var/cache \
    --mount=type=tmpfs,dst=/tmp \
    echo "cachebust=${FEATURES_CACHEBUST}" >/dev/null && \
    ENABLE_FIRSTBOOT_USER=${ENABLE_FIRSTBOOT_USER} \
    /ctx/build_files/install-features.sh "${FEATURES}"

# 6) Lint
RUN bootc container lint