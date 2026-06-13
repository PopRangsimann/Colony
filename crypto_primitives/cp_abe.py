"""
Pairing-Based CP-ABE  --  Waters'11 (LSSS, Type-3 pairing)
==========================================================
Classical Ciphertext-Policy ABE replacing the previous lattice / dual-Regev
construction.  This is the standard expressive CP-ABE of Waters (CCS 2011),
realized over an asymmetric (Type-3) bilinear group.

What changed from the lattice version
--------------------------------------
  * The per-attribute dual-Regev KEMs are gone.  Security now rests on a
    bilinear Diffie-Hellman style assumption in a pairing group, with the
    attribute hash H modeled as a random oracle, rather than on LWE.
  * The scheme is now COLLUSION-RESISTANT in the standard CP-ABE sense.  The
    lattice version issued the same per-attribute secret to every user, so two
    users could pool attributes; Waters'11 binds every key to a fresh per-user
    randomizer t, so keys from different users cannot be combined to satisfy a
    policy neither user satisfies alone.  The bundled self-test checks this.
  * The message layer is a clean KEM/DEM: a random GT blinding factor
    e(g,h)^{a s} is reconstructed by an authorized decryptor and used to wrap
    the AES key.  No per-bit ciphertexts.

What stayed the same
--------------------
  * The policy-tree -> monotone span program (Lewko-Waters MSP) machinery is
    reused unchanged.  Only the secret-sharing field moved from GF(2) to the
    prime field Z_p of the pairing group, which is what Waters'11 requires.
  * The public method surface is preserved so this is a drop-in replacement:
        setup(), keygen(msk, attrs)
        encrypt(k_aes, policy) / decrypt(ct, sk)
        ree_build_policy(), tee_partial_encrypt(), ree_finalize_ct()
        policy_eval(), cpabe_decrypt()
        hash_attribute(attr)
        full_encrypt(cpabe, k_aes, policy) / full_decrypt(cpabe, ct, sk)
        self._pub[attr]   (now H(attr), a public G1 point)
    The legacy policy form {"type": "AND"/"OR", "attributes": [...]} is still
    accepted, as are nested tree policies.

Fields that did NOT carry over
------------------------------
  The lattice-only raw fields self.A, self.n, self.q and the per-attribute
  master-secret store self._sec do not exist in a pairing scheme and were
  removed.  self.p (the group order) replaces self.q's role.  If
  phase5_fog_node/ours.py or phase6_user_decrypt/ours.py read self.A / self.n /
  self.q / self._sec directly, those call sites need updating; the method-level
  API above is unaffected.

Backend and performance
-----------------------
  The pairing backend is py_ecc's optimized BN128 (pip-installable, pure
  Python).  It is correct but slow: a pairing is ~0.3 s, so decrypting an
  ell-row policy costs roughly (2*ell + 1) * 0.3 s.  CP-ABE here protects one
  result key per retrieval, so this is a micro-benchmark cost, not a per-packet
  cost.  For fast runs, the same construction maps directly onto charm-crypto's
  'waters11' (C-backed PBC) if it can be installed locally; only the small
  backend helper block below would change.

Construction (Type-3, e: G1 x G2 -> GT)
---------------------------------------
Setup:    a, alpha <- Z_p ;  MPK = (g, h, g^a, e(g,h)^alpha) ;  H: attr -> G1
KeyGen(S): t <- Z_p ;  K = h^{alpha + a t} ,  L = h^t ,  K_x = H(x)^t  for x in S
Encrypt((M,rho), k_aes):
          s <- Z_p ;  v = (s, y_2, ..., y_k) ;  lambda_i = <M_i, v>
          blind = e(g,h)^{alpha s} ;  C' = g^s
          C_i = g^{a lambda_i} * H(rho(i))^{-r_i} ,  D_i = h^{r_i}
          wrap = KDF(blind, C') ;  c_aes = k_aes XOR wrap
Decrypt:  find I and weights omega over Z_p with sum omega_i lambda_i = s
          blind = e(C',K) / prod_i ( e(L,C_i) e(D_i,K_{rho(i)}) )^{omega_i}
          k_aes = c_aes XOR KDF(blind, C')
"""

from __future__ import annotations

import hashlib
import secrets
from typing import Any, Dict, List, Optional, Tuple

import py_ecc.optimized_bn128 as bn
from py_ecc.optimized_bn128 import (
    G1, G2, FQ, FQ2, FQ12,
    add, multiply, neg, pairing, normalize, is_on_curve,
    curve_order, field_modulus, b as B1, b2 as B2,
)

# ─────────────────── Parameters ─────────────────────────────────────
# The constructor still accepts the old lattice kwargs (n, m, q) and ignores
# them, so existing instantiations such as LatticeCPABE() or
# LatticeCPABE(n=32, q=3329) keep working.
GROUP_ORDER = curve_order          # prime p; the LSSS field
FIELD_MOD   = field_modulus        # base-field prime P for point coordinates


# ═══════════════════════════════════════════════════════════════════
#                     Pairing-group backend helpers
# ═══════════════════════════════════════════════════════════════════
# Isolating every backend call here keeps the rest of the file independent of
# the specific pairing library; swapping to charm-crypto or BLS12-381 only
# touches this block.

def _rand_zp() -> int:
    return secrets.randbelow(GROUP_ORDER - 1) + 1


def _hash_to_g1(attr: str) -> Tuple:
    """
    Random-oracle hash of an attribute string to a G1 point with unknown
    discrete log (try-and-increment).  BN128 G1 has prime order (cofactor 1),
    so any on-curve point is a valid group element.
    """
    ctr = 0
    while True:
        digest = hashlib.sha256(f"{attr}|{ctr}".encode()).digest()
        x = int.from_bytes(digest, "big") % FIELD_MOD
        rhs = (pow(x, 3, FIELD_MOD) + 3) % FIELD_MOD          # y^2 = x^3 + 3
        y = pow(rhs, (FIELD_MOD + 1) // 4, FIELD_MOD)         # P % 4 == 3
        if (y * y - rhs) % FIELD_MOD == 0:
            pt = (FQ(x), FQ(y), FQ(1))
            assert is_on_curve(pt, B1)
            return pt
        ctr += 1


def _g1_to_list(pt: Tuple) -> List[int]:
    x, y = normalize(pt)
    return [int(x.n), int(y.n)]


def _g1_from_list(coords: List[int]) -> Tuple:
    pt = (FQ(coords[0]), FQ(coords[1]), FQ(1))
    if not is_on_curve(pt, B1):
        raise ValueError("deserialized G1 point not on curve")
    return pt


def _g2_to_list(pt: Tuple) -> List[List[int]]:
    x, y = normalize(pt)
    return [[int(c) for c in x.coeffs], [int(c) for c in y.coeffs]]


def _g2_from_list(coords: List[List[int]]) -> Tuple:
    x = FQ2((coords[0][0], coords[0][1]))
    y = FQ2((coords[1][0], coords[1][1]))
    pt = (x, y, FQ2.one())
    if not is_on_curve(pt, B2):
        raise ValueError("deserialized G2 point not on curve")
    return pt


def _gt_to_bytes(elt: FQ12) -> bytes:
    return b"|".join(str(int(c)).encode() for c in elt.coeffs)


def _kdf(blind: FQ12, cprime: Tuple, length: int) -> bytes:
    """Counter-mode KDF over the KEM material; supports any key length."""
    seed = b"cpabe-waters11-kdf|" + _gt_to_bytes(blind) \
        + b"|" + repr(_g1_to_list(cprime)).encode()
    out = bytearray()
    ctr = 0
    while len(out) < length:
        out += hashlib.sha256(seed + b"|" + ctr.to_bytes(4, "big")).digest()
        ctr += 1
    return bytes(out[:length])


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def _hash_attr_int(attr, p: int) -> int:
    raw = attr.encode() if isinstance(attr, str) else attr
    return int(hashlib.sha256(raw).hexdigest(), 16) % p


# ═══════════════════════════════════════════════════════════════════
#                Policy Tree  +  Lewko-Waters MSP
# ═══════════════════════════════════════════════════════════════════
# A policy is a nested dict:
#     leaf:  {"attr": "Engineer"}
#     AND:   {"op": "AND", "children": [<policy>, ...]}
#     OR:    {"op": "OR",  "children": [<policy>, ...]}
# The legacy form {"type": "AND"/"OR", "attributes": [...]} is also accepted.

def _legacy_to_tree(policy: Dict[str, Any]) -> Dict[str, Any]:
    if "op" in policy or "attr" in policy:
        return policy
    op = policy.get("type", "AND").upper()
    attrs = policy.get("attributes", [])
    leaves = [{"attr": a} for a in attrs]
    if len(leaves) == 1:
        return leaves[0]
    return {"op": op, "children": leaves}


def _binarize(node: Dict[str, Any]) -> Dict[str, Any]:
    """Rewrite n-ary AND/OR into right-folded binary trees; leaves unchanged."""
    if "attr" in node:
        return node
    op = node["op"].upper()
    children = [_binarize(c) for c in node["children"]]
    if len(children) == 1:
        return children[0]
    result = children[-1]
    for ch in reversed(children[:-1]):
        result = {"op": op, "children": [ch, result]}
    return result


def build_msp_from_tree(tree: Dict[str, Any]) -> Tuple[List[List[int]], List[str]]:
    """
    Lewko-Waters construction: policy tree -> (M, rho).

    Returns the MSP matrix M (entries in {-1, 0, 1}) as a list of rows and the
    attribute label rho(i) for each row.  A user whose attribute set satisfies
    the tree can find weights omega_i over Z_p with
        sum_{i : rho(i) in S} omega_i * M_i = (1, 0, ..., 0).
    """
    tree = _binarize(tree)
    rows: List[List[int]] = []
    labels: List[str] = []

    def recurse(node, vec, next_col):
        if "attr" in node:
            rows.append(list(vec))
            labels.append(node["attr"])
            return next_col

        op = node["op"].upper()
        left, right = node["children"]

        if op == "OR":
            nc = recurse(left, vec, next_col)
            nc = recurse(right, vec, nc)
            return nc

        if op == "AND":
            new_col = next_col
            padded = list(vec) + [0] * (new_col - len(vec))
            left_vec = padded + [1]
            right_vec = [0] * new_col + [-1]
            nc = recurse(left, left_vec, new_col + 1)
            nc = recurse(right, right_vec, nc)
            return nc

        raise ValueError(f"Unknown op: {op}")

    total_cols = recurse(tree, [1], 1)
    M = [[0] * total_cols for _ in rows]
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            M[i][j] = v
    return M, labels


# ─────────── Linear algebra over Z_p ────────────────────────────────

def _solve_zp(A: List[List[int]], b: List[int], p: int) -> Optional[List[int]]:
    """Solve A x = b over Z_p by Gaussian elimination. Returns x or None."""
    m = len(A)
    n = len(A[0]) if m else 0
    aug = [[A[i][j] % p for j in range(n)] + [b[i] % p] for i in range(m)]

    pivot_cols: List[int] = []
    row = 0
    for col in range(n):
        sel = None
        for r in range(row, m):
            if aug[r][col] % p != 0:
                sel = r
                break
        if sel is None:
            continue
        aug[row], aug[sel] = aug[sel], aug[row]
        inv = pow(aug[row][col], -1, p)
        aug[row] = [(v * inv) % p for v in aug[row]]
        for r in range(m):
            if r != row and aug[r][col] % p != 0:
                f = aug[r][col] % p
                aug[r] = [(aug[r][j] - f * aug[row][j]) % p for j in range(n + 1)]
        pivot_cols.append(col)
        row += 1

    for r in range(row, m):
        if aug[r][-1] % p != 0:
            return None

    x = [0] * n
    for i, col in enumerate(pivot_cols):
        x[col] = aug[i][-1] % p
    return x


def authorized_row_set(M: List[List[int]], rho: List[str],
                       user_attrs: set) -> Optional[List[int]]:
    """Return the candidate rows the user owns, if they can span e_1 over Z_p."""
    candidate_rows = [i for i in range(len(rho)) if rho[i] in user_attrs]
    if not candidate_rows:
        return None

    cols = len(M[0])
    sub = [M[i] for i in candidate_rows]
    target = [0] * cols
    target[0] = 1
    # Need omega with sub^T omega = target.
    AT = [[sub[r][c] for r in range(len(sub))] for c in range(cols)]
    if _solve_zp(AT, target, GROUP_ORDER) is None:
        return None
    return candidate_rows


# ═══════════════════════════════════════════════════════════════════
#                          CP-ABE (Waters'11)
# ═══════════════════════════════════════════════════════════════════

class CPABE:
    """
    Waters'11 Ciphertext-Policy ABE over a Type-3 pairing group.

    Public attributes preserved for back-compat:
        self.p              -- group order (the LSSS field); replaces old self.q
        self._pub[attr]     -- H(attr), a public G1 point
    Master secret (a, alpha) lives in self._msk and is also returned by setup().
    """

    def __init__(self, n: Any = None, m: Any = None, q: Any = None, **kwargs):
        # n, m, q accepted and ignored: they were lattice parameters.
        self.p = GROUP_ORDER
        self.g = G1
        self.h = G2
        self._pub: Dict[str, Tuple] = {}      # attr -> H(attr) in G1 (public)
        self._msk: Dict[str, int] = {}
        self._mpk: Dict[str, Any] = {}
        self.setup()

    # ─────── Setup / Registration ───────

    def setup(self) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """Return (MPK, MSK).  MSK = (a, alpha); MPK = (g, h, g^a, e(g,h)^alpha)."""
        a = _rand_zp()
        alpha = _rand_zp()
        self._msk = {"a": a, "alpha": alpha}
        self._mpk = {
            "g":  self.g,
            "h":  self.h,
            "ga": multiply(self.g, a),
            "egg_alpha": pairing(self.h, self.g) ** alpha,   # e(g,h)^alpha in GT
        }
        return self._mpk, self._msk

    def _H(self, attr: str) -> Tuple:
        pt = self._pub.get(attr)
        if pt is None:
            pt = _hash_to_g1(attr)
            self._pub[attr] = pt
        return pt

    def hash_attribute(self, attr: str) -> int:
        """Integer attribute hash in Z_p (kept for compatibility)."""
        return _hash_attr_int(attr, self.p)

    def keygen(self, msk, attributes) -> Dict[str, Any]:
        """
        Issue a user secret key for the attribute set.

        Returns a dict keyed by attribute (K_x = H(x)^t in G1), plus reserved
        entries "__K__" and "__L__" (in G2) carrying the per-user components
        K = h^{alpha + a t} and L = h^t.  Reserved keys are filtered out
        wherever the user's attribute set is read.
        """
        if not msk:
            msk = self._msk
        a = msk["a"]
        alpha = msk["alpha"]
        t = _rand_zp()                                   # fresh per-user randomizer

        K = multiply(self.h, (alpha + a * t) % self.p)   # h^{alpha + a t}
        L = multiply(self.h, t % self.p)                 # h^t
        sk: Dict[str, Any] = {"__K__": K, "__L__": L}
        for x in attributes:
            sk[x] = multiply(self._H(x), t % self.p)     # K_x = H(x)^t
        return sk

    @staticmethod
    def _user_attrs(sk: Dict[str, Any]) -> set:
        return {k for k in sk.keys() if not k.startswith("__")}

    # ─────── Encrypt / Decrypt ───────

    def encrypt(self, k_aes: bytes, policy: Dict[str, Any]) -> Dict[str, Any]:
        policy_pkg = self.ree_build_policy(policy)
        tee_out = self.tee_partial_encrypt(k_aes, policy_pkg)
        return self.ree_finalize_ct(policy_pkg, tee_out)

    def ree_build_policy(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """Public policy expansion: tree -> (M, rho)."""
        tree = _legacy_to_tree(policy)
        M, rho = build_msp_from_tree(tree)
        return {"M": M, "rho": list(rho), "tree": tree, "policy": policy}

    def tee_partial_encrypt(self, k_aes: bytes,
                            policy_pkg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Randomized encryption core: sample the secret s, LSSS-share it over
        Z_p, and emit the per-row group elements plus the KEM-wrapped key.
        """
        M = policy_pkg["M"]
        rho = policy_pkg["rho"]
        ell = len(M)
        k = len(M[0])
        p = self.p

        for a in rho:
            self._H(a)                                   # ensure H(attr) known

        s = _rand_zp()
        v = [s] + [_rand_zp() for _ in range(k - 1)]
        lam = [sum(M[i][j] * v[j] for j in range(k)) % p for i in range(ell)]

        blind = self._mpk["egg_alpha"] ** s              # e(g,h)^{alpha s}
        cprime = multiply(self._mpk["g"], s)             # C' = g^s

        ci_list: List[Tuple] = []
        di_list: List[Tuple] = []
        for i in range(ell):
            r_i = _rand_zp()
            ci = add(multiply(self._mpk["ga"], lam[i] % p),
                     multiply(self._H(rho[i]), (-r_i) % p))   # g^{a lam} H^{-r}
            di = multiply(self._mpk["h"], r_i % p)            # h^{r}
            ci_list.append(ci)
            di_list.append(di)

        wrap = _kdf(blind, cprime, len(k_aes))
        c_aes = _xor(k_aes, wrap)

        return {
            "cprime": cprime,
            "Ci": ci_list,
            "Di": di_list,
            "c_aes": list(c_aes),
        }

    def ree_finalize_ct(self, policy_pkg: Dict[str, Any],
                        tee_out: Dict[str, Any]) -> Dict[str, Any]:
        """Public packaging: serialize all group elements to JSON-safe lists."""
        M = policy_pkg["M"]
        rho = policy_pkg["rho"]
        tree = policy_pkg["tree"]
        policy = policy_pkg["policy"]

        return {
            "M":           [list(row) for row in M],
            "rho":         list(rho),
            "cprime":      _g1_to_list(tee_out["cprime"]),
            "Ci":          [_g1_to_list(c) for c in tee_out["Ci"]],
            "Di":          [_g2_to_list(d) for d in tee_out["Di"]],
            "c_aes":       list(tee_out["c_aes"]),
            "policy_type": policy.get("type") or tree.get("op", "AND"),
        }

    def decrypt(self, ct: Dict[str, Any],
                sk_u: Dict[str, Any]) -> Optional[bytes]:
        pe = self.policy_eval(ct, sk_u)
        if pe is None:
            return None
        return self.cpabe_decrypt(ct, sk_u, pe)

    # ─────── Split decryption (for phase6 timing) ───────

    def policy_eval(self, ct: Dict[str, Any],
                    sk_u: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Public LSSS reconstruction over Z_p.  Returns {"I": [...],
        "omega": [...]} or None if the user's attributes do not satisfy policy.
        """
        M = ct["M"]
        rho = ct["rho"]
        user_attrs = self._user_attrs(sk_u)

        I = authorized_row_set(M, rho, user_attrs)
        if I is None:
            return None

        cols = len(M[0])
        sub = [M[i] for i in I]
        target = [0] * cols
        target[0] = 1
        AT = [[sub[r][c] for r in range(len(sub))] for c in range(cols)]
        omega = _solve_zp(AT, target, self.p)
        if omega is None:
            return None
        return {"I": list(I), "omega": list(omega)}

    def cpabe_decrypt(self, ct: Dict[str, Any],
                      sk_u: Dict[str, Any],
                      pe: Dict[str, Any]) -> Optional[bytes]:
        """
        Secret decryption: reconstruct the GT blinding factor with pairings and
        unwrap the AES key.
            blind = e(C', K) / prod_i ( e(L, C_i) e(D_i, K_{rho(i)}) )^{omega_i}
        """
        rho = ct["rho"]
        I = pe["I"]
        omega = pe["omega"]
        p = self.p

        K = sk_u["__K__"]
        L = sk_u["__L__"]
        cprime = _g1_from_list(ct["cprime"])

        prod = FQ12.one()
        for idx, row_i in enumerate(I):
            w = omega[idx] % p
            if w == 0:
                continue
            ci = _g1_from_list(ct["Ci"][row_i])
            di = _g2_from_list(ct["Di"][row_i])
            kx = sk_u[rho[row_i]]
            term = pairing(L, ci) * pairing(di, kx)
            prod = prod * (term ** w)

        blind = pairing(K, cprime) * prod.inv()

        wrap = _kdf(blind, cprime, len(ct["c_aes"]))
        return _xor(bytes(ct["c_aes"]), wrap)


# Back-compat alias: existing imports of LatticeCPABE keep working.
LatticeCPABE = CPABE


# ═══════════════════════════════════════════════════════════════════
#               Back-compat wrapper functions
# ═══════════════════════════════════════════════════════════════════

def full_encrypt(cpabe: CPABE, k_aes: bytes,
                 policy: Dict[str, Any]) -> Dict[str, Any]:
    return cpabe.encrypt(k_aes, policy)


def full_decrypt(cpabe: CPABE, ct: Dict[str, Any],
                 sk_u: Dict[str, Any]) -> Optional[bytes]:
    return cpabe.decrypt(ct, sk_u)


# ═══════════════════════════════════════════════════════════════════
#                          Self-test
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import time

    cpabe = CPABE()
    mpk, msk = cpabe._mpk, cpabe._msk
    key = hashlib.sha256(b"result-data-key").digest()   # 32-byte AES key
    print("AES key       :", key.hex())

    # (1) AND policy, authorized user
    pol_and = {"type": "AND", "attributes": ["Engineer", "FogAdmin"]}
    ct = full_encrypt(cpabe, key, pol_and)
    sk_full = cpabe.keygen(msk, ["Engineer", "FogAdmin"])
    t = time.time()
    rec = full_decrypt(cpabe, ct, sk_full)
    print("AND  authorized:", rec == key, "  (%.0f ms)" % ((time.time() - t) * 1000))

    # (2) AND policy, user missing an attribute -> denied
    sk_part = cpabe.keygen(msk, ["Engineer"])
    print("AND  missing   :", full_decrypt(cpabe, ct, sk_part) is None)

    # (3) Collusion: two users each holding one of the two required attributes
    #     pool their keys; this must NOT recover the key.
    u1 = cpabe.keygen(msk, ["Engineer"])
    u2 = cpabe.keygen(msk, ["FogAdmin"])
    franken = {"__K__": u1["__K__"], "__L__": u1["__L__"],
               "Engineer": u1["Engineer"], "FogAdmin": u2["FogAdmin"]}
    print("collusion fails:", full_decrypt(cpabe, ct, franken) != key)

    # (4) OR policy: a single matching attribute suffices
    pol_or = {"type": "OR", "attributes": ["Engineer", "FogAdmin"]}
    ct_or = full_encrypt(cpabe, key, pol_or)
    print("OR   single-attr:", full_decrypt(cpabe, ct_or,
                                            cpabe.keygen(msk, ["FogAdmin"])) == key)

    # (5) Nested tree: (A AND B) OR C
    pol_tree = {"op": "OR", "children": [
        {"op": "AND", "children": [{"attr": "Engineer"}, {"attr": "FogAdmin"}]},
        {"attr": "Auditor"},
    ]}
    ct_tree = full_encrypt(cpabe, key, pol_tree)
    print("tree via Auditor:", full_decrypt(cpabe, ct_tree,
                                            cpabe.keygen(msk, ["Auditor"])) == key)
    print("tree via A+B    :", full_decrypt(cpabe, ct_tree,
                                            cpabe.keygen(msk, ["Engineer", "FogAdmin"])) == key)
    print("tree via A only :", full_decrypt(cpabe, ct_tree,
                                            cpabe.keygen(msk, ["Engineer"])) is None)