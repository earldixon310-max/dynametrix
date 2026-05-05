"""
SpinPhase pipeline implementation, frozen at the v1 test version.

Pre-registration: docs/PRE_REGISTRATION_GW_v1.md (Section 4)

This module is FROZEN. Per Section 10.1 of the pre-registration, the code
must not be modified between commit and the recording of all 100 Z-scores.
Bugs found post-freeze are accepted as features of v1, or addressed in v2
under a fresh pre-registration.

Implementation notes:

 * Whitening (Section 4.1) uses gwpy's TimeSeries.whiten with a Welch PSD
   estimated from the segment itself, Hann window, 4-second FFT length,
   2-second overlap (50%).

 * STFT (Section 4.2) uses scipy.signal.stft with a 0.25-second Hann window,
   87.5% overlap, yielding 4 Hz frequency resolution.

 * Chirp track (Section 4.3) is sampled at the STFT time-bin cadence
   between segment_midpoint - 0.40 s and segment_midpoint + 0.05 s, with
   exponential frequency interpolation between (35 Hz) and (220 Hz).

 * Phase coherence (Section 4.4) implements the Δt search via frequency-
   domain phase rotation rather than literal time-bin re-indexing. The
   pre-reg's "X_L1(t_k - Δt, f_k)" is computed as
   X_L1(t_k, f_k) * exp(2π i f_k Δt). This is mathematically equivalent
   to a sub-bin time shift and is necessary because the Δt search range
   (±10 ms) is finer than the STFT time-bin width (~31 ms).

 * Null distribution (Section 4.5) shifts L1 cyclically via numpy.roll
   for each s in {±1, ±2, ..., ±25} seconds (50 shifts). The cyclic wrap
   discontinuity is accepted as part of v1 because the same null
   procedure is applied identically to all segments, and the chirp-track
   window remains fixed near the segment midpoint, far from the wrap
   boundary.
"""

import numpy as np
from scipy.signal import stft as scipy_stft


# --- Pre-registered configuration (Section 4) ---

SAMPLE_RATE_HZ = 4096
SEGMENT_DURATION_S = 32

# Whitening (Section 4.1)
WHITEN_PSD_FFTLENGTH_S = 4
WHITEN_PSD_OVERLAP_S = 2

# STFT (Section 4.2)
STFT_WINDOW_S = 0.25
STFT_OVERLAP_FRAC = 0.875
STFT_FREQ_RESOLUTION_HZ = 4  # = SAMPLE_RATE_HZ / (STFT_WINDOW_S * SAMPLE_RATE_HZ)

# Chirp track (Section 4.3)
CHIRP_T1_OFFSET_S = -0.40   # relative to segment midpoint
CHIRP_F1_HZ = 35
CHIRP_T2_OFFSET_S = +0.05
CHIRP_F2_HZ = 220

# Δt search (Section 4.4)
DT_RANGE_MS = 10
DT_STEP_MS = 0.5

# Null distribution (Section 4.5): ±1, ±2, ..., ±25 seconds = 50 shifts
NULL_SHIFTS_S = list(range(1, 26)) + list(range(-25, 0))

# Numerical guard for division (Section 6.1)
NULL_EPSILON = 1e-8


# --- Helpers ---------------------------------------------------------------

def chirp_track_freq(t_offset_s):
    """Return the chirp track frequency at time `t_offset_s` (relative to midpoint).

    Exponential interpolation per Section 4.3:
        f(t) = f1 * (f2/f1)^((t - t1) / (t2 - t1))
    """
    return CHIRP_F1_HZ * (CHIRP_F2_HZ / CHIRP_F1_HZ) ** (
        (t_offset_s - CHIRP_T1_OFFSET_S)
        / (CHIRP_T2_OFFSET_S - CHIRP_T1_OFFSET_S)
    )


def whiten_strain(strain_ts):
    """Whiten a gwpy TimeSeries per Section 4.1."""
    return strain_ts.whiten(
        fftlength=WHITEN_PSD_FFTLENGTH_S,
        overlap=WHITEN_PSD_OVERLAP_S,
        window="hann",
    )


def compute_stft(whitened_array, sample_rate=SAMPLE_RATE_HZ):
    """Compute STFT per Section 4.2.

    Returns (freqs, times, stft_complex), where stft_complex has shape
    (n_freqs, n_times) and `times` is in seconds from the start of
    `whitened_array`.
    """
    nperseg = int(STFT_WINDOW_S * sample_rate)
    noverlap = int(STFT_OVERLAP_FRAC * nperseg)
    freqs, times, stft_complex = scipy_stft(
        whitened_array,
        fs=sample_rate,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
        boundary=None,
        padded=False,
    )
    return freqs, times, stft_complex


def chirp_track_indices(stft_times, segment_midpoint_t):
    """Return list of (time_idx, freq_idx) along the chirp track.

    For each STFT time bin t_k within
    [midpoint + CHIRP_T1_OFFSET_S, midpoint + CHIRP_T2_OFFSET_S],
    determines the chirp frequency at t_k and snaps to the nearest
    STFT frequency bin (4 Hz spacing).
    """
    chirp_start_t = segment_midpoint_t + CHIRP_T1_OFFSET_S
    chirp_end_t = segment_midpoint_t + CHIRP_T2_OFFSET_S
    in_window = (stft_times >= chirp_start_t) & (stft_times <= chirp_end_t)
    time_indices = np.where(in_window)[0]

    indices = []
    for ti in time_indices:
        t_offset = stft_times[ti] - segment_midpoint_t
        f_target = chirp_track_freq(t_offset)
        fi = int(round(f_target / STFT_FREQ_RESOLUTION_HZ))
        indices.append((int(ti), int(fi)))
    return indices


def phase_coherence_at_dt(stft_h1, stft_l1, freqs, chirp_indices, dt_seconds):
    """Compute phase coherence at a given Δt per Section 4.4.

    Δt is implemented as a frequency-domain phase rotation:
        X_L1(t_k - Δt, f_k) ≡ X_L1(t_k, f_k) * exp(2π i f_k Δt)
    so that
        Δφ_k(Δt) = arg(X_H1) - arg(X_L1) - 2π f_k Δt
    and
        C_φ(Δt) = |(1/N) Σ_k exp(i · Δφ_k(Δt))|
    """
    N = len(chirp_indices)
    if N == 0:
        return 0.0

    cumsum = 0.0 + 0.0j
    two_pi_dt = 2.0 * np.pi * dt_seconds
    for (ti, fi) in chirp_indices:
        x_h1 = stft_h1[fi, ti]
        x_l1 = stft_l1[fi, ti]
        f_k = freqs[fi]
        phi_diff = np.angle(x_h1) - np.angle(x_l1) - two_pi_dt * f_k
        cumsum += np.exp(1j * phi_diff)

    return float(abs(cumsum / N))


def search_dt(stft_h1, stft_l1, freqs, chirp_indices):
    """Search Δt over [-DT_RANGE_MS, +DT_RANGE_MS] in DT_STEP_MS steps.

    Returns (M_obs, best_dt_s).
    """
    n_steps = int(round(2 * DT_RANGE_MS / DT_STEP_MS)) + 1
    dts_ms = np.linspace(-DT_RANGE_MS, DT_RANGE_MS, n_steps)

    coherences = np.empty(n_steps, dtype=float)
    for i, dt_ms in enumerate(dts_ms):
        coherences[i] = phase_coherence_at_dt(
            stft_h1, stft_l1, freqs, chirp_indices, dt_ms / 1000.0
        )

    best_idx = int(np.argmax(coherences))
    return float(coherences[best_idx]), float(dts_ms[best_idx] / 1000.0)


def compute_null_distribution(whitened_h1_array, whitened_l1_array,
                              sample_rate=SAMPLE_RATE_HZ):
    """Compute null M_obs values via cyclic time shifts of L1.

    Returns a numpy array of 50 M_obs values, one per shift in
    NULL_SHIFTS_S. The H1 STFT and chirp indices are computed once
    and reused across shifts.
    """
    segment_midpoint_t = len(whitened_h1_array) / sample_rate / 2.0
    freqs, times, stft_h1 = compute_stft(whitened_h1_array, sample_rate)
    chirp_indices = chirp_track_indices(times, segment_midpoint_t)

    null_M_values = np.empty(len(NULL_SHIFTS_S), dtype=float)
    for k, shift_s in enumerate(NULL_SHIFTS_S):
        shift_samples = int(round(shift_s * sample_rate))
        l1_shifted = np.roll(whitened_l1_array, shift_samples)
        _, _, stft_l1_shifted = compute_stft(l1_shifted, sample_rate)
        m_shift, _ = search_dt(stft_h1, stft_l1_shifted, freqs, chirp_indices)
        null_M_values[k] = m_shift

    return null_M_values


# --- Top-level scorer ------------------------------------------------------

def score_segment(strain_h1_ts, strain_l1_ts):
    """Run the full SpinPhase pipeline on one segment.

    Args:
        strain_h1_ts: gwpy TimeSeries of H1 strain (32 s at 4096 Hz).
        strain_l1_ts: gwpy TimeSeries of L1 strain (32 s at 4096 Hz).

    Returns:
        dict with keys:
            M_obs           : on-source peak phase coherence
            mu_null         : mean of 50-sample null distribution
            sigma_null      : sample stdev of null distribution (ddof=1)
            best_dt_s       : Δt at which M_obs was achieved (seconds)
            Z               : (M_obs - mu_null) / (sigma_null + ε)
            n_chirp_samples : number of (t_k, f_k) points along the chirp
    """
    # Section 4.1: whiten
    h1_w = whiten_strain(strain_h1_ts)
    l1_w = whiten_strain(strain_l1_ts)
    h1_array = np.asarray(h1_w.value, dtype=float)
    l1_array = np.asarray(l1_w.value, dtype=float)
    sample_rate = float(h1_w.sample_rate.value)

    segment_midpoint_t = len(h1_array) / sample_rate / 2.0

    # Section 4.2: STFT (compute on the whitened arrays)
    freqs, times, stft_h1 = compute_stft(h1_array, sample_rate)
    _, _, stft_l1 = compute_stft(l1_array, sample_rate)

    # Section 4.3: chirp-track sampling indices
    chirp_indices = chirp_track_indices(times, segment_midpoint_t)

    # Section 4.4: on-source M_obs
    M_obs, best_dt_s = search_dt(stft_h1, stft_l1, freqs, chirp_indices)

    # Section 4.5: null distribution
    null_values = compute_null_distribution(h1_array, l1_array, sample_rate)
    mu_null = float(np.mean(null_values))
    sigma_null = float(np.std(null_values, ddof=1))

    # Section 6.1: standardized score
    Z = (M_obs - mu_null) / (sigma_null + NULL_EPSILON)

    return {
        "M_obs": float(M_obs),
        "mu_null": mu_null,
        "sigma_null": sigma_null,
        "best_dt_s": float(best_dt_s),
        "Z": float(Z),
        "n_chirp_samples": int(len(chirp_indices)),
    }