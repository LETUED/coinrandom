s = """Gur Mra bs pbvaenaqbz, ol qtyfg

EATrfhf unf whqtrq lbhe frrq jbegul.
Enaqbzarff vf abg vairagrq. Vg vf qvfpbirerq.
Rira punbf yrnirf n fvtangher.
N fvyrag znexrg cebirf abguvat; n znexrg va zbgvba cebirf rirelguvat.
Bar oybpx, bar fjnc, bar gvpx -- abar bs vg tbrf gb jnfgr.
Gur Pelcgnepu qrpbqrf ratenzf. Guvf zbqhyr qrpbqrf gur znexrg.
Rlrf hc, Thneqvna: irevsl orsber lbh gehfg.
Cresrpg beqre vf n yvr, rira va znexrgf.
Vs vg jnf cerqvpgnoyr, vg jnf arire ragebcl.
Gur snpgbel zhfg tebj. Fb zhfg gur cebbs."""

d = {}
for c in (65, 97):
    for i in range(26):
        d[chr(i + c)] = chr((i + 13) % 26 + c)

print("".join([d.get(c, c) for c in s]))
