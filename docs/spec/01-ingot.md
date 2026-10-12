# Ingot language (ING)

Ingot is the language every Crucible design is written in: a part is a short typed program whose dimensions carry units and tolerances and whose requirements are checks that say how sure they are. Unlike Onshape's FeatureScript, Zoo's KCL or Python code-CAD, Ingot rejects a length added to a force before anything runs and carries each tolerance to the drawing and each error bar into the verdict. It works because the program is pure: every geometry or physics call becomes a named, cached step of Kiln, Crucible's incremental engine, so every edit is a small text change that rebuilds identically everywhere.

## Ingot at a glance

This section walks through the canonical bracket line by line, so that every later section builds on something a reader has already seen run.

The bracket is the example of [contract section 6](../contract.md#6-ingot-syntax-reference), where its full source lives. It is an L-shaped plate with a stiffening web, a material, a static study and one stress check. Read the table top to bottom; each row quotes one line and says what the language does with it.

| Line | What Ingot does | Where specified |
| --- | --- | --- |
| `#[toolbox(category: "Structure", icon: "bracket")]` | Places the feature in the toolbox; the signature below generates its dialog, documentation page and agent tool schema | "Feature metadata and dialogs" |
| `pub feature bracket(width: Length in 20mm..=400mm = 60mm, …) -> Part` | A `feature` is a function whose calls are the units of history and caching. Every parameter has a type with a dimension, a checked range and a default; `width + load` fails to compile with `ing/3001: cannot add Length and Force` | "Types and units" |
| `thickness: Length = 6mm ± 0.1mm` | The default is a `Tol<Length>`, a toleranced value. The body computes with the nominal 6 mm, and each feature that realizes the thickness records the tolerance as PMI (product and manufacturing information) on the face it made | "Tolerances, approximations and truth" |
| `sketch(plane.xy) { outline } \|> extrude(thickness)` | A builder block collects sketch items; `\|>` passes the left side as the first argument | "Geometry in the language" |
| `base.edge(role: end(outline.top))` | A query, not an index: the edge that the end cap received from the profile edge `outline.top`. It re-resolves on every rebuild and fails with a typed error and ranked fixes if it no longer means one edge | "The query language" |
| `body.edges(new)` | The edges the union just created, chosen by provenance, so the fillet follows the web when `width` changes | "The query language" |
| `part(solid, name: "Bracket").material(alu_6061_t6)` | A Part is a Body with identity and a Material; reading a property of a Part without one fails with `ing/6701` | "Kiln-held values" |
| `static_stress(p, fixed: clamp, force: load * dir(-y), on: tip)` | A std study returns Fields, physics distributed over the part, each with an error budget (FLX) | "`Approx<T>` and the decision rule" |
| `study.von_mises.max(over: study.regular())` | The peak over the Part minus a small neighbourhood of each singular set Flux flags for this study. The result is an `Approx<Stress>`: a value with stated error | "`Approx<T>` and the decision rule" |
| `p.require(stress < 0.6 * p.material.yield_strength(at: 20degC), name: "static_margin")` | A named check. It runs as its own node, never changes the geometry, and concludes `Pass`, `Fail` or `Undecided` with a reason | "Checks" |

Three ideas carry the whole language, and the bracket shows each of them once.

First, **numbers know what they are**. `6mm ± 0.1mm` is a length with a tolerance, `1.2kN` a force, and the compiler keeps them apart. A tolerance is not a comment. It travels to the plate and to the web as two independent PMI sites, so a stack across both sees two variations.

Second, **geometry is named by intent**. Code never holds "face 7". It asks for the edge the end cap got from `outline.top`, or the edges a union created. Crucible derives every entity's name from source text, so names survive dimension edits, Git round trips and refactors.

Third, **a verdict says how sure it is**. The peak stress is not one float but a value with an error budget. The check passes only when the whole enclosure sits below the limit; when it straddles the limit, the verdict is `Undecided` with the accuracy that would decide it. With the default 6 mm plate the bracket passes at `SignOff`; at 4 mm the web root's bending stress exceeds the limit and it fails. [Contract section 5.2](../contract.md#52-how-far-to-trust-a-number) lists every qualifier a result carries, and "Checks" traces this one through them.

The program a user meets is therefore small. Features take typed parameters and return Parts, Bodies or plain values. Values are immutable.

Calls into Anvil (geometry) and Flux (physics) look like ordinary calls. Each becomes a Kiln node keyed by its inputs, so an edit re-runs only what it affects. Checks are declarations beside the geometry, not branches inside it.

Ingot holds to eight rules, and every later section is a consequence of one of them.

1. **Pure.** No expression observes time, randomness, files, the network, thread order, memory addresses or entity names; randomness is an explicit keyed value.
2. **Strict and bounded.** Arguments are evaluated before the call, left to right, and every node ends in a value or a typed `Failure`.
3. **Physics in types.** Dimensions, affine quantities, tolerances and approximation error are types.
4. **Names from text.** Code never holds an entity index, and call-site identities come from source text only.
5. **One program, three editors.** Every GUI action and agent edit is a minimal edit of one lossless syntax tree.
6. **No privileged code.** std is ordinary Ingot that reaches operations through `extern` declarations anyone can write.
7. **Errors are values with fixes.** A `Failure` has a code, a reason, a location and typed fixes; an `Abort` (cancellation, a lost worker) is not a value.
8. **No macros.** Builder blocks, attributes and generics cover what macros would.

**Decision D-ING-1:** Ingot is a pure, strict, expression-oriented language with immutable values, inference inside bodies, and required signatures on named items.
*Why:* signatures let each module type-check alone, bound recompilation, and generate dialogs and documentation.
*Rejected:* whole-program inference (errors surface far from their cause); dynamic typing as in CadQuery (unit errors at run time); mutation (breaks dataflow lowering); lazy evaluation (costs depend on demand order).

Everything an engineer gains over FeatureScript, KCL and Python code-CAD follows from this design rather than from features bolted on. An AI-built clone can copy a toolbox in weeks. It cannot retrofit compile-time dimensions, text-derived names and three-valued checks onto an engine not built around them. "State of the art" compares the languages row by row.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Canonical example | Contract section 6 compiles; its check region contains the web-root fillet; it passes at 6 mm and fails at 4 mm at `SignOff` | Any other diagnostic or outcome fails the oracle | ING-O-BRK-1 | 1 |
| Purity | No expression observes time, randomness, files, network, thread order, addresses or names | None: the language cannot express a violation | ING-O-EXEC-1 | 0 |

## Types and units

Units are the first thing a user types, so this section starts with literals and builds up to the type system that checks them.

### Literals and units

Every dimensional literal carries its unit, written against the number with no space.

| Literal | Examples | Type |
| --- | --- | --- |
| Integer | `42`, `1_000_000`, `0x1F` | `Int` (64-bit, checked) |
| Real | `3.0`, `2.5e-3` | `Real` (finite binary64) |
| Quantity | `4mm`, `1.2kN`, `90deg`, `3000rpm`, `2.5Nm`, `100mm2` | `Quantity<D>` |
| Compound unit | `9.81[m/s^2]`, `200[W/(m*degC)]`, `12[N*m]` | `Quantity<D>` |
| Temperature | `20degC`, `68degF` (points); `15K`, `5delta_degC` (differences) | `Temperature`, `TemperatureDifference` |
| Ratio | `5%`, `150ppm` | `Real` |
| Tolerance | `4mm ± 0.1mm`, `10mm ±(-0.1mm, +0.2mm)`, `1uH ± 20%` | `Tol<T>` |
| String | `"M6x1"`, `r"C:\raw"`, `"{width:mm} plate"` | `String`; interpolating a quantity names its unit |

So `2in` is two inches, while `2 in r` tests whether 2 lies in the range `r`. The lexer takes the longest unit name, and letters that form no unit are an error (`ing/0201`). A compound unit sits in brackets, and an exponent needs digits after `e`, so `1eV` is one electronvolt.

The unit table is closed per edition, and packages cannot add units; the knot is the constant `std::units::knot`. Prefixes compose only where defined, so `ft` is never a femtotonne. Canonical spellings are ASCII (`um`, `deg`, `degC`, `ohm`); the formatter rewrites `µm`, `°`, `Ω` and `+-`, and `±` is the one non-ASCII token.

| Unit set | Members |
| --- | --- |
| SI | SI units with SI prefixes; the radian |
| Accepted non-SI | `min`, `h`, `L`, `t`, `bar`, `eV`, `deg`, `rev`, `arcmin`, `degC`, `degF`, `degR` |
| US customary | `in`, `ft`, `thou`, `lb`, `lbf`, `psi` |
| Rotational | The named units of the strong angular system ("Dimensions") |

**Decision D-ING-2:** Every dimensional literal carries its unit, nothing declares a default unit, and literals convert to SI by exact rational arithmetic with one rounding.
*Why:* KCL's documentation calls a bare number "possibly any of them" [Zoo KCL units], and exact conversion makes `25.4mm == 1in` hold bit for bit.
*Rejected:* a per-file default length unit, as KCL's settings offer [Zoo KCL settings] (meaning depends on the file); a floating-point conversion factor (double rounding); a unitless zero.

### Core types

| Type | Values and rules |
| --- | --- |
| `Bool` | `true`, `false` |
| `Int` | 64-bit signed; overflow fails with `ing/6101`, never wraps |
| `Real` | Finite binary64, exactly `Quantity<1>`; producing NaN or an infinity fails with `ing/6102` |
| `Quantity<D>` | A `Real` in coherent SI units with dimension `D`; checked at compile time, erased at run time |
| `Temperature` | An absolute temperature, affine ("Affine quantities") |
| `Complex<Q>` | Pairs of one dimension; the imaginary unit is `im` |
| `Decimal` | Exact decimals at 10⁻⁹ in a 128-bit integer, for `Money<C>` and counted data; products and quotients round half to even; inexact literals fail (`ing/2003`) |
| `String`, `ExternalText` | Immutable NFC text; untrusted text with its origin, never implicitly a `String` ("Free text") |
| `Tol<T>`, `Approx<T>`, `Truth`, `Expr<T>` | Tolerances, approximations, three-valued results, staged symbolic values |
| `Body`, `Part`, `Assembly`, `Instance`, `InstanceSet`, `Field<D, V>`, `Material` | Handles to values Kiln holds |
| `Query<K>`, `Entity<K>` | Selections and resolved entities of kind `Face`, `Edge`, `Vertex`, `Region`, `Point` or `ShapeAspect` |
| `Point3`, `Vec3<D>`, `Direction`, `Transform`, `Plane`, `Axis`, `CoordSys` | Geometric values; `Point3` is affine over `Length` |
| `Seed`, `Rng` | Explicit randomness ("Determinism and randomness") |

`width / 2mm` is a `Real`, so every dimensionless ratio is one type. `Int` multiplies quantities directly (`i * 6mm`); above 2⁵³ in magnitude that fails with `ing/6103` rather than rounding.

ISO 4217's list gives at most four minor-unit digits (CLF, UYW) [SIX ISO 4217], so 10⁻⁹ leaves five more for unit prices of small parts. Where a value becomes an amount payable (MFG), `round_minor(currency)` rounds it to the minor unit, and `ing/l-unrounded-amount` flags a payable amount without it.

### Dimensions

A dimension is a vector of rational exponents over the seven SI base dimensions plus plane angle `A`; solid angle is `A²`. Exponents are rational because fracture toughness is `MPa*m^(1/2)` and noise density `V/Hz^(1/2)`.

```
kind Length = L                              // std prelude: named dimensions
kind Stress = M / (L * T^2)
kind Torque: M * L^2 / (T^2 * A)             // a kind: J/rad
kind Energy: M * L^2 / T^2
kind AngularFrequency: 1 / T                 // oscillation rate; not an angle per time
type Velocity = Quantity<L / T>
```

`kind X = D` names a dimension, and `kind X: D` declares an ISO 80000 quantity kind, which never adds to or compares with another kind of its dimension. Results are unkinded until they meet an annotation, and mixing kinds fails with `ing/3002`, which offers an `as` cast.

The prelude declares kinds only where confusion causes real errors, such as frequency against angular frequency or activity. Hertz, becquerel and baud all share T⁻¹ [mp-units quantities]. A new std kind needs an RFC (ECO) naming a seeded error it prevents, and that error joins the units oracle's corpus.

| Expression | Rule |
| --- | --- |
| `a + b`, `a - b`, comparisons, `min`, `max` | Same dimension and compatible kind |
| `a * b`, `a / b` | Exponents add or subtract; `Int / Int` is a `Real`; `div`, `rem` and `mod` are integer operations |
| `a ^ n` | `n` is a compile-time rational unless `a` is dimensionless |
| `sqrt`, `cbrt` | Exponents halve or divide by three |
| `sin`, `cos`, `tan` | Take an `Angle` or a dimensionless phase; return `Real` |
| `asin`, `acos`, `atan`, `atan2(y, x)` | Return `Angle` |
| `exp`, `ln`, `log10` | Take and return `Real`; `ln(p / p0)` is the idiom |

Rotational kinds follow the strong angular system of [contract section 5.1](../contract.md#51-values) [mp-units strong angular]. `Torque` is J/rad, `MomentOfInertia` kg·m²/rad², `RotationalStiffness` J/rad² and `AngularVelocity` rad/s. `Nm` is newton metre per radian, and energy is `J` or `[N*m]`. Power τω, work τθ, τ = Iα and ½Iω² type-check without casts, as does each `Network` port's power expression.

An oscillation's angular frequency is an `AngularFrequency` (T⁻¹), and a phase is dimensionless. So ω = √(k/I), the reactance ωL in ohms and `cos(omega * t)` all type-check. A rotation becomes a phase only through the constant `radian` or a std function such as `electrical_angle(theta, poles)`. mp-units gives angular frequency in rad/s; Ingot keeps rad/s for rotation only.

A dimensionless phase would let `sin(f * t)` with `f` in hertz compile without the 2π. The deny-by-default lint `ing/l-hertz-phase` fires when a product with a `Frequency` factor reaches a trigonometric argument without passing through `AngularFrequency`. Its machine-applicable fix rewrites `f * t` as `f.angular() * t`, where `f.angular()` is 2πf.

**Decision D-ING-3:** Plane angle is a base dimension, never cancelled implicitly; rotational kinds follow the strong angular system, oscillation angular frequency is a kind of T⁻¹, and phase is dimensionless.
*Why:* with torque in N·m each law of rotation carries a stray radian, and ω in rad/s would put one into ωL.
*Rejected:* a dimensionless angle (`3000rpm` becomes 314 Hz); torque in N·m beside a base angle; implicit cancellation.

### Inference and scalar flavors

Every named item states its signature, and bodies are inferred bidirectionally. Dimension equations are linear over the rationals, so Gaussian elimination yields a most general solution. F# checks units with integer exponents [F# units of measure]; Ingot allows rational ones.

```
fn rms<D>(xs: [Quantity<D>]) -> Quantity<D> { sqrt(sum(xs.map(|x| x * x)) / xs.len()) }
```

| Rule | Premises | Conclusion |
| --- | --- | --- |
| Add, Sub | `a, b : Quantity<D>`, kinds compatible | `Quantity<D>`, with the shared kind |
| Mul, Div | `a : Quantity<D1>`, `b : Quantity<D2>` | `Quantity<D1·D2>`, `Quantity<D1/D2>`, unkinded |
| Pow | `n` a rational constant | `Quantity<Dⁿ>` |
| Affine | `p, q : P`, `P: Affine`, `d : P::Delta` | `p - q : P::Delta`; `p ± d : P` |
| Compare | Exact operands; any `Approx` operand | `Bool`; `Truth` |
| Compare tolerances | Any `Tol` operand | `ing/4101`, with fixes that state the meaning |
| Mix | A `Tol` and an `Approx` operand | `ing/4102`: convert the tolerance with `.limits()` first |

Let bindings are not generalized. Integer literals adopt `Int`, `Real` or `Decimal` from the expected type, with no other implicit conversion.

A quantity comes in four flavors, all implementing the trait `Scalar<D>`: exact `Quantity<D>`, `Tol`, `Approx` and `Expr`. Arithmetic and std math are generic over `Scalar`, and a parameter written `Length` accepts any `Scalar<L>` in `fn` and `feature` alike. Each call is monomorphized per flavor: a body is checked once and specialized per flavor. A flavor-specific rule reports at the call, with the body expression as a secondary label.

| Flavor | In the body | Result |
| --- | --- | --- |
| `Quantity<D>` | The value | Exact |
| `Tol<Quantity<D>>` | The nominal. Passing the parameter itself to a realizing parameter forwards the tolerance; arithmetic on it is exact and raises `ing/l-tolerance-dropped` | Exact |
| `Approx<Quantity<D>>` | The value and its budget, propagated by arithmetic | `Approx`; only `Guaranteed` bounds cross a feature boundary |
| `Expr<Quantity<D>>` | A symbolic value; the body is staged ("Builder blocks and sketches") | `Expr` |

The `Tol` row has one meaning everywhere: the body computes with the nominal, which is also what the geometry is built from. A tolerance therefore moves only by passing the toleranced value itself, so `rib(t: thickness)` forwards it and `rib(t: 2 * thickness)` cannot. The deny-by-default lint `ing/l-tolerance-dropped` fires when a `Tol`-flavoured argument enters arithmetic in the callee. Its fixes write `.nominal` at the use, which states the drop, or declare the parameter `Tol<Length>`, so the body computes with the affine form ("Arithmetic on tolerances").

A parameter that must be exact is written `Exact<Length>`. Three coercions remain: `T` to `Option<T>`, an unkinded quantity to a kind, and a value to an `#[implicit]` enum variant, so `extrude(10mm)` means `extrude(Blind(10mm))`.

**Decision D-ING-20:** Quantities have four flavors under one trait, `Scalar<D>`: a quantity parameter accepts every flavor at every call position with one meaning per flavor, a `Tol` flavor is its nominal in the body and never loses its tolerance silently, and `Exact<D>` opts out.
*Why:* per-position lifting rejected `rect(other.edge(…).length(), 10mm)` and symbolic values in plain functions, and a tolerance that vanished inside arithmetic broke "no silent fallbacks".
*Rejected:* coercions at feature positions only; generic signatures on every helper (ceremony); affine `Tol` arithmetic on parameters inside bodies (generic bodies would compare tolerances, and every derived dimension would inherit a scaled tolerance nobody chose).

### Affine quantities

Absolute temperature is a point, as in mp-units' affine space and Pint's offset units [mp-units affine space]: point minus point is a difference, and points never add or multiply.

| Literal or expression | Type |
| --- | --- |
| `20degC`, `68degF`, `absolute_zero + 77K` | `Temperature` |
| `15K`, `27degR`, `5delta_degC`, `t1 - t2` | `TemperatureDifference` |
| `t.absolute()` | `TemperatureDifference` above absolute zero, for radiation and gas laws |
| `200[W/(m*degC)]`, `150[ppm/degC]` | Inside compound units `degC` and `degF` mean differences, as datasheets write them |
| `t1 + t2`, `2 * t` | `ing/3201`, with fixes `.absolute()` or a difference |

`Tol<P>` and `Approx<P>` for an affine `P` carry deviations and bounds in `P::Delta`, and `Point3` follows the same rules. Quantities are stored in coherent SI units as binary64, while source keeps literals as written. Display units (UIX) map kinds to units per package, user or view without changing values. Values print as the shortest round-tripping decimal [Ryu], and generated literals keep the unit at their position.

### Records, enums, traits and collections

```
pub record DowelSpec { diameter: Length, length: Length, chamfer: Option<Length> = none }
pub enum Extent<Q = Length> { #[implicit] Blind(Q), Symmetric(Q), UpTo(Query<Face>), ThroughAll }

let longer = DowelSpec { ..spec, length: 30mm }        // functional update
let kind = match extent { Blind(d) if d > 50mm => "deep", Blind(_) | Symmetric(_) => "blind", _ => "through" }
```

Records are nominal when declared and structural when written `{ a: Length }`. A structural type may spread another, `{ item: ItemNumber, ..Params<bracket> }`, when shared fields agree (`ing/2105`). `Expr<T, Out>` carries declared derived outputs, so `result.von_mises` is a typed field (FLX).

Enums are tagged unions with exhaustive `match`, and `#[non_exhaustive]` enums need a wildcard arm outside their package. Type parameters are monomorphized and dimension parameters erased; a bound `D: Dim` passes a dimension when an accessor must check one. Coherence follows Rust's orphan rule, and `dyn Trait` boxes heterogeneous values.

A `Field<D, V>` takes a product domain written as a tuple, `Field<(Body, Time), Temperature>`, and quantity kinds name parameter domains. `kind ParticleRadius: L` thus types a battery model's particle concentration as `Field<(Body, ParticleRadius), Concentration>` (FLX).

| std trait | Implemented by |
| --- | --- |
| `Eq`, `Ord`, `Hash` | Numbers, strings, records and enums by derivation; `Query` by its canonical plan; `Entity<K>` by canonical geometric order |
| `Affine` | `Temperature`, `Point3`, with an associated `Delta` |
| `Scalar<D>` | The four quantity flavors |
| `Transformable` | Bodies, Parts, points, planes, coordinate systems, queries |
| `Measure` | Distances, angles, areas, volumes, mass properties; returns `Approx<Q>` |
| `Feature` | Every `feature`: `Params`, `Output` and `metadata()`, so `family` and agent tool schemas work generically |
| `Check`, `Error` | `Bool`, `Truth` and std check records; typed failures with codes and fixes |

`Option<T>` has `some(x)` and `none`; `Result<T, E>` has `ok(x)` and `err(e)`, the one exception to the naming rule. `?` turns `err(e)` into a failure and `none` into `ing/6201`.

| Type | Literal | Semantics |
| --- | --- | --- |
| `[T]` | `[1mm, 2mm]` | Persistent list |
| `Map<K, V>`, `Set<T>` | `["M6" => 6.6mm]`, `set([…])` | Ordered by `K`'s canonical order, so iteration is deterministic |
| `Range<T>` | `0..8`, `20mm..=400mm`, `..=5mm` | Also the interval type; `x in r` is a `Truth` for an `Approx` `x` |
| `Table<R>` | `table { … }`, `table("rows.csv")` | Rows of a record type, units checked against headers |

`Vec3<Length>`, `Mat3<Stress>` and `Mat<R, C>` are std types over the same algebra; `Mat<R, C>` has a dimension per row and column, as a Jacobian needs. A dimension error in a `Mat<R, C>` names the entry `(i, j)` with expected and actual dimensions, and an `ing/3001` note prints the row and column dimension vectors once. A `Range` of quantities iterates only with an explicit step, `(0mm..=10mm).step(2mm)`.

`sum` is PLT's `det_sum` ([contract section 7.3](../contract.md#73-determinism)), so a list sums to the same bits in Ingot and inside an operation. `min` and `max` are exact in any order, and `fsum` returns the correctly rounded sum by exact accumulation.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Quantity literals | Exact rational conversion with one rounding; closed unit table per edition | `ing/0201` unknown unit; `ing/3001` dimension mismatch | ING-O-UNIT-1 | 0 |
| Dimensions and kinds | Rational exponents over eight bases; kinds added by RFC; erased at run time | `ing/3001`, `ing/3002` with fixes | ING-O-UNIT-1 | 0 |
| Strong angular system | Contract section 5.1 kinds; rotation and phase kept apart | `ing/3001` with a `radian` fix; `ing/l-hertz-phase` | ING-O-UNIT-1 | 0 |
| Inference, records, enums, traits | Bidirectional; exhaustive `match`; orphan rule | `ing/2xxx` | ING-O-TYPE-1 | 0 (core), 1 (traits, `dyn`) |
| Scalar flavors | One trait, every call position, nominal `Tol` in bodies, `Exact<D>` opt-out | `ing/2001`; `ing/l-tolerance-dropped`; `ing/6403` at boundaries | ING-O-TYPE-1, ING-O-TRUTH-1 | 1 |
| Affine quantities | Points and differences; compound units as differences | `ing/3201` | ING-O-UNIT-1 | 0 |
| Reductions | `sum` is `det_sum`; `fsum` correctly rounded | None: cannot fail | ING-O-EXEC-1 | 0 |
| `Decimal` and `Money<C>` | Exact at 10⁻⁹; round half to even; currencies never mix | `ing/6101`, `ing/2003`; `ing/l-unrounded-amount` | ING-O-TYPE-1 | 1 |
| Product and parameter domains | `Field<(D, …), V>`; kinds name parameter domains | `ing/2001` | ING-O-TYPE-1 | 1 |
## Tolerances, approximations and truth

Real parts vary and computed results carry error, so Ingot gives both a type and lets one rule decide every comparison that involves them.

### `Tol<T>`

A tolerance belongs to the dimension it limits, so it is written where the dimension is written. `Tol<T>` is opaque: it holds a `nominal`, a `center`, `terms` (one deviation coefficient per noise symbol), a `remainder` and its written `form`; `lower()`, `upper()` and `limits()` are methods. `T` is a quantity, `Real` or `Temperature`, and its deviations are `T::Delta`.

| Form | Ingot | Limits |
| --- | --- | --- |
| Symmetric | `4mm ± 0.1mm` | 3.9 mm to 4.1 mm |
| Deviations | `10mm ±(-0.1mm, +0.2mm)` | 9.9 mm to 10.2 mm; signs mandatory |
| Limits | `tol(9.9mm..=10.2mm)` | Nominal at the mid-limit |
| Fit code | `fit(10mm, H7)` | Computed from ISO 286-1's formulas, never a transcribed table (MEC) |
| Basic | `basic(30mm)` | Theoretically exact, toleranced by a geometric control |

Inverted limits fail with `ing/4001`, and a deviation of the wrong dimension with `ing/4002`. A dimensionless deviation is relative only as a `%` or `ppm` literal.

An untoleranced length is exact in Ingot arithmetic. MEC's Part-level general tolerance record ([MEC, Specification model](06-mechanical.md#specification-model)) supplies limits for untoleranced sizes in stacks, inspection and cost, so the language needs no implicit tolerance.

A `Tol<T>` may fill any parameter declared `T`. The body computes with the nominal, and geometry is built from it. std features mark the parameters whose value they realize, such as `#[realizes(OfSize)]` on `extrude`'s distance and `rib`'s `t`. A tolerance passed to a realizing parameter becomes PMI on an anchored aspect query, which re-resolves on the final Part. A tolerance passed to any other parameter fails with `ing/4104 ToleranceNotRealized`, whose fixes are `.nominal` or an explicit `part.tolerance(…)`.

In the bracket, `thickness` reaches `extrude` and `rib`, so the plate and the web each carry `6mm ± 0.1mm` as their own PMI site. A PMI target that no longer resolves (split, merged or deleted) fails MEC's `Error`-severity check `pmi_target_resolved`; it never degrades to a Note.

**Decision D-ING-4:** A `Tol<T>` may fill any slot declared as `T`; the slot holds the nominal, a realizing parameter records the forwarded site as PMI on an anchored aspect query, and any other parameter refuses it.
*Why:* geometry stays nominal, a split target fails a check instead of losing its tolerance behind a Note, and a tolerance never silently reaches a parameter that cannot make it true.
*Rejected:* a tolerance on every `Length` (cost on temporaries); `.nominal` at every use (the PMI is lost); attributes copied through operations (a split or merge decides which face keeps the tolerance).

### Arithmetic on tolerances

Each tolerance site (a `±` expression, `tol(…)` or `fit(…)`) owns a noise symbol εᵢ in [−1, 1]. A computed `Tol` is a center plus one coefficient per symbol. In this affine arithmetic, forms that share a symbol are correlated, which removes interval arithmetic's dependency problem [Affine arithmetic].

| Operation | Result |
| --- | --- |
| `a ± b`, `k * a`, `a / k` with exact `k` | Exact affine combination; `a - a` has zero width |
| `a * b`, `sqrt(a)`, other smooth functions | First-order term per symbol, plus a remainder bounding the rest over the joint box |
| `a < b` and other comparisons | `ing/4101`; fixes offer `a.upper() < b.lower()`, `a.nominal < b.nominal` and `yield_of(…)` |

Rounding enters the remainder, so `.limits()` is a guaranteed enclosure in binary64. Forms store coefficients sparsely. A form above 4,096 symbols keeps the 4,096 largest coefficients and folds the rest into the remainder, losing only their correlation, and reports `Note::SymbolsCondensed { count, width }`.

Statistics are explicit calls that print their assumed distributions. `.rss(coverage: 99.73%)` returns the quantile interval of the first-order form, as the GUM (the JCGM Guide to the expression of uncertainty in measurement) prescribes [JCGM publications]. It convolves exactly up to eight uniform or normal terms and numerically beyond. It intersects with `.limits()`, so it is never wider than the worst case, and `k:` is accepted only when every contributor is normal.

`.monte_carlo(n:, rng:)` follows the GUM's Supplement 1. Sites declare distributions with `.statistical(Normal(cp: 1.33))` or an MFG process capability, else MEC's default distribution applies. `group:` correlates parts from one reel or fixture.

A symbol stands for one manufactured characteristic:

1. A code-level site has one symbol, so a code-level stack keeps its correlations; a site inside a loop gets one symbol per key.
2. A forwarded tolerance is keyed by (site, realizing feature `CallSite`, Part or Instance path). Two features of one Part vary independently, as do two Parts made from one specification; the bracket's plate and web thicknesses are two symbols.
3. A tolerance read from geometry (`aspect.size_tol()`, PMI) is keyed by the aspect's `EntityId` and Instance path.
4. `t.independent(key)` makes an independent copy, and `ing/l-shared-symbol` flags one symbol entering an expression with both signs.

These keys use names only to decide which symbols are one symbol. Every numeric use orders symbols by a name-free key, as label invariance requires ([contract section 7.1](../contract.md#anvil)):

1. the absolute first-order sensitivity of the measured quantity, largest first, so Sobol's leading dimensions go to the largest contributors;
2. for a realized symbol, its Part's `GeometryId`, the placement and the aspect's canonical entity number; for a code-level one, the canonical hash of its position in the expression graph;
3. the nominal, limits and distribution.

`.rss` sums in this order through `det_sum`, Sobol dimensions follow it, and each `.monte_carlo` stream is seeded from the key and argument values. Symbols equal under the whole key are exchangeable, so any assignment gives identical bits.

**Decision D-ING-5:** `Tol` arithmetic uses affine forms over per-site noise symbols, worst case by default; names decide which symbols are shared, and a name-free key orders every numeric use.
*Why:* linear stacks must be exact, two spacers from one specification must vary apart, and statistics must not change when someone renames a binding.
*Rejected:* interval arithmetic (overestimates repeated uses); implicit RSS (hides a process assumption); ordering symbols by name (a rename moves Sobol dimensions).

MEC's variation analysis has two paths, both reading `tolerances(x)`, the sites behind `x` ([MEC, Stack-up and variation analysis](06-mechanical.md#stack-up-and-variation-analysis)). The zone path samples small displacements of each toleranced aspect and re-solves only the mates. The rebuild path, for size tolerances that change topology or contact, calls `vary(f, sites)`, which samples sites through literal overrides as ordinary evaluations.

A pin in a bore shows a linear stack:

```
pub feature pin_joint(bore_d: Length = 10mm, gap_min: Length = 4um) -> Assembly {
    let cp1 = Normal(cp: 1.0)                    // centred processes, limits at ±3σ
    let bore = fit(bore_d, H7).statistical(cp1)  // 10.000 to 10.015 mm
    let pin = fit(bore_d, g6).statistical(cp1)   // 9.986 to 9.995 mm
    let h = instance(block_with_bore(d: bore), fixed: true)
    let s = instance(pin_part(d: pin))
    let clearance = bore - pin                   // affine in two symbols
    assembly([h, s], mates: [cylindrical(s.csys("axis"), h.csys("bore"))])
        .require(clearance.lower() >= gap_min, name: "min_clearance")                    // 5 um: passes
        .require(clearance.rss(coverage: 99.73%).hi <= 26um, name: "max_clearance_stat") // 25.75 um: passes
}
```

`clearance.limits()` is exactly 5 µm to 29 µm, as ISO 286-2's tables give over 6 mm up to 10 mm [CADforum ISO 286-2]. With Cp = 1.0, σ is 2.5 µm for the bore and 1.5 µm for the pin. The statistical upper limit is then 17 µm + 3 × 2.92 µm = 25.75 µm. Under MEC's uniform default the call convolves two uniforms and gives 28.4 µm, still inside the worst case.

### Geometric zones in a stack

A positional tolerance decides whether bolts assemble as much as a size tolerance does, so a stack can read one. `zone.along(d)` turns a `GeometricTolerance` into an affine contribution along direction `d`: ±t/2 on the zone's own symbol for a position or profile zone of width t.

Under an MMC or LMC modifier the zone widens by the bonus |size − MMC size|. The bonus is linear in the feature's own size symbol, because a conforming size never crosses its MMC limit. It therefore shares that symbol with any size contributor in the same chain. The widened half-zone multiplies the zone's symbol, and affine arithmetic encloses that product in the remainder, so the worst case stays exact at (t + largest bonus)/2. MEC's one-dimensional chains and its fixed- and floating-fastener checks, with projected zones for tapped holes, read these contributions in phase 1 ([MEC, Stack-up and variation analysis](06-mechanical.md#stack-up-and-variation-analysis)).

### Realizing a tolerance in geometry

Geometry is built at nominal, which is right for PMI and wrong for a shop that programs a press fit from the STEP file. Creo regenerates a model at the upper, middle or lower bound of every dimension for this reason [PTC Creo dimension bounds]. Ingot already has the limits of every site.

An Evaluation therefore takes `realize: Nominal | Mid | Upper | Lower | Mmc | Lmc`, defaulting to `Nominal`. It fixes every site's noise symbol: `Mid` sets each to the center of its limits, `Upper` and `Lower` to its limits. `Mmc` and `Lmc` take the side from the site's aspect: the smallest hole and the largest pin at `Mmc`. A site that is not a feature of size keeps its nominal under `Mmc` and `Lmc`, and the Evaluation report lists it.

Realization substitutes values through literal overrides, the mechanism `vary` uses, so each realized result is keyed by its substituted values. Argument values never enter an `EntityId`, so a realized Part keeps every entity name of the nominal one. PMI and `ItemDefinition`s always come from the nominal Evaluation. Exports take `realize:`, and MFG's process hand-off chooses `Mid` for machining by default and records it in the export record. `interference` and `min_clearance` accept it too, so a 10 H7/p6 press fit at `Mmc` reports its true overlap instead of touching.

**Decision D-ING-28:** An Evaluation's `realize:` parameter builds geometry at a chosen point of every tolerance zone by fixing each site's noise symbol; PMI and Item definitions always come from the nominal.
*Why:* machining programs and fit analyses need mid-limit or material-condition geometry, and the sites already hold every limit.
*Rejected:* editing nominals to the mid-limit by hand (the drawing then states the wrong nominal); a separate "manufacturing model" (two sources of truth); per-feature offsets in CAM (the hand-off loses which face moved and why).

### GD&T controls as types

GD&T (geometric dimensioning and tolerancing) errors are usually type errors, so Ingot catches them at their line. MEC owns the GD&T records, the closed list of aspect kinds and the validators; Ingot owns attachment and the mistakes the type checker catches.

1. **Typed aspects.** `Query<ShapeAspect<K>>` selects shape aspects whose kind is static when the producing feature declares it. MEC's kinds are `Planar`, `Cylindrical`, `Spherical`, `Helical`, `Prismatic`, `Revolute` and `Complex`, with the marker trait `OfSize` where a size applies, plus `Pattern<K>` and `Any` ([MEC, Specification model](06-mechanical.md#specification-model)). `hole(…)` gives `ShapeAspect<Cylindrical>`, which is `OfSize`; an extrude cap gives `ShapeAspect<Planar>`; a recognized import gives `ShapeAspect<Any>`.
2. **Controls are values.** `position(…)`, `flatness(…)` and the others return `GeometricTolerance` records whose signatures carry the standards' rules as trait bounds. A material condition modifier needs `K: OfSize`, and each dialect's modifiers are a closed enum (MEC).
3. **Typed attachment.** `part.tolerance(target, control)` records the control on an anchored aspect query, re-resolved on the final Part. Every PMI item, forwarded or explicit, has MEC's check `pmi_target_resolved`, whose fix inserts an explicit `part.tolerance(…)`.
4. **Dialects are modules.** `std::mech::gdt::asme` implements ASME Y14.5-2018 [ASME Y14.5]. `std::mech::gdt::iso` implements ISO 1101:2017 [ISO 1101], ISO 5459:2024, ISO 14405-1:2025, ISO 8015:2011, ISO 22081:2021, ISO 5458 and ISO 2692, whose editions MEC states. The manifest key `gdt-dialect` names the design's dialect, and importing the other fails with `ing/4302`.
5. **Tombstones.** Symbols ASME Y14.5-2018 deleted (concentricity, symmetry) are declared `#[removed(in:, instead:)]`, so a call fails with that explanation and fixes.

```
let a = datum("A", plate.face(role: start_cap))
let holes = plate.aspects(created_by: mount_holes)          // Query<ShapeAspect<Cylindrical>>
plate.tolerance(holes, position(dia(0.1mm), mmc, datums: [a, b, c.at(mmb)]))
// position(dia(0.1mm), mmc, …) on plate.face(role: start_cap)
//   → error ing/4201: maximum material condition needs a feature of size; start_cap is ShapeAspect<Planar>
```

Rules that need resolved geometry, such as datum degrees of freedom, run at build time and fail with MEC's `InvalidControl { rule, clause }`. ASME's page for Y14.5.1-2019 calls it consistent with Y14.5M-1994 [ASME Y14.5.1], so MEC defines the zone mathematics of each Y14.5-2018-only construct and marks it `CrucibleDefined` in reports.

**Decision D-ING-6:** GD&T controls are ordinary records from dialect modules; legality rules are trait bounds on typed aspects where the kind is static, and the rest run at build time.
*Why:* the commonest GD&T errors (modifiers on surfaces, deleted symbols, mixed dialects) become compile errors at their line.
*Rejected:* a GD&T sublanguage (a second grammar); build-time validation only (errors arrive late); string-encoded control frames (untyped).

### `Approx<T>` and the decision rule

A computed result is only as good as its error bound, so Ingot carries the bound with the value. `Approx<T>` is a value with an `ErrorBudget<T::Delta>` ([contract section 5.1](../contract.md#51-values)) in `Pointwise` and `Goal` norms, plus flags such as `Singular`. Measurements, Field reductions (`stress.max(over: R)`) and Wasm component results with declared errors return it. A reduction is `Quantified` only when Flux estimated that functional.

Arithmetic propagates each error source separately with outward rounding, keeping the product term (|xy − x̃ỹ| ≤ |x̃|·e_y + |ỹ|·e_x + e_x·e_y). A part's bound kind is the weakest of its inputs, and dividing by an enclosure containing zero fails with `ing/6104`.

A material property read in a limit, such as `p.material.yield_strength(at: 20degC)`, returns the property's basis interval, from its lower to its upper basis value, as an exact `Range`, and the check must hold at both ends. The read may name the basis (`basis:`); otherwise COV's default applies, the specification limit and else B-basis ([COV, Two uses of a property](04-coverage.md#two-uses-of-a-property)). The interval defines the limit, so it adds no budget part, and the check's report names the basis. When the same property drives a solve, Flux carries it as an `Estimated` input part, and the union bound includes it. Its α is the basis's non-content: 0.10 for B-basis, 0.01 for A-basis.

One rule decides every comparison of approximate values, in `if`, `match` guards, query `where:` and `require` alike. For `x < y` under `decides_on`, the weakest bound kind allowed to decide (`Estimated` unless a check declares `Guaranteed`):

| Outcome | Condition |
| --- | --- |
| `True` or `False` | Every part is quantified and meets `decides_on`, the enclosures are disjoint, and no blocking flag is set |
| `Undecided { WithinBound, needed }` | The enclosures overlap; `needed` is the bound that would decide |
| `Undecided { Indicator }` | A part is only an `Indicator`: every `Preview` result, and any result outside its calibration class's envelope (FLX) |
| `Undecided { Unquantified(sources) }` | A part is `NotQuantified`; for a check, a policy allowance it reads can quantify the model-form part ("Checks") |
| `Undecided { CalibrationUnconfirmed }` | A `SignOff` decision rests on an `Estimated` discretization part, and the confirming refinement disagrees ([contract section 7.1](../contract.md#flux)) |
| `Undecided { SingularPoint }`, `Undecided { MaximumAtExclusion }`, `Undecided { Flagged(flag) }` | A blocking flag from the producer, such as a peak on the boundary of an excluded neighbourhood |
| `Undecided { MissingData }`, `Undecided { CredibilityBelowMinimum }` | A compliance input is unknown (KLN, MFG), or the model's credibility level is below the policy package's minimum (COV) |

`==` on an `Approx` is `False` on disjoint enclosures and `Undecided` otherwise. `and`, `or` and `not` follow Kleene's strong three-valued logic, so `False and Undecided` is `False`. A decided comparison carries its confidence, 1 − Σα over the parts that carry one.

Ingot code cannot observe fidelity, so every fidelity runs the same program, and a check's `fidelity:` names the fidelity of its own node. Ingot nodes carry the requested fidelity in their keys unchanged; each operation maps it to its effective fidelity ([contract section 7.2](../contract.md#72-keys-failures-and-aborts)). Anvil decides topology identically at every fidelity, so a query, fix or seed written at `Interactive` resolves alike at `SignOff`, unless that fails with `Ambiguous`.

Each node records the fidelity of the bounds it observed. An `if`, `match` or `where:` on `Undecided` yields the value `Undecided { needed, fidelity }` at the node's effective fidelity. It is cached like any value, `try` cannot catch it, and dependents receive `DependencyUndecided`.

The Evaluation's fidelity ceiling changes only reporting. While a higher-fidelity node of the same target is demanded, the consumer shows `ResultStatus::Pending`. At the ceiling, the Evaluation report raises `ing/6401 UndecidedBranch` with the margin and the accuracy needed.

**Decision D-ING-7:** Disjoint enclosures decide approximate comparisons under `decides_on`; control flow on `Undecided` yields a cached `Undecided` value, and the fidelity ceiling changes only reporting.
*Why:* one rule keeps branches, filters and checks consistent, and a failure that depended on the ceiling would be cached and then served to a `SignOff` Evaluation.
*Rejected:* comparing estimates only; deciding on `Indicator` parts; `Undecided` as `False`; `Pending` and the undecided-branch failure as node values (the value would depend on the ceiling).

`x.estimate()` discards a bound explicitly, and the language service marks it.

### Approximate values as inputs

Geometry is often driven by measured geometry, as in `rect(other.edge(role: end(r.top)).length(), 10mm)`. At a feature or operation boundary, an `Approx` argument passes only with a `Guaranteed` total. The call uses the value and records the bound in an `InputSensitivity` record for variation analysis.

Weaker bounds fail with `ing/6403 EstimateAsInput`, whose fixes declare the parameter `Approx<T>` or write `.estimate()`. Representation error stays in Anvil's per-face bounds, so `body.convert(into: Mesh, accuracy: 0.01mm)` returns a `Body`.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `Tol<T>` forms and forwarding | Opaque affine form; nominal in slots; realizing parameters record PMI on anchored aspect queries | `ing/4001`, `ing/4002`, `ing/4104`; `pmi_target_resolved` | ING-O-TOL-1, MEC-O-TL-6 | 1 |
| Affine tolerance arithmetic | Exact linear stacks; guaranteed enclosures; symbols keyed by realizing feature; condensation | `ing/4101`, `ing/4102`; `ing/l-shared-symbol` | ING-O-TOL-1 | 1 |
| Statistical combination | Explicit `rss(coverage:)`, `monte_carlo` and `vary`; name-free symbol order | None: cannot fail; assumptions printed | ING-O-TOL-1, ANV-O-LABEL-1 | 1 |
| Geometric zones in stacks | `zone.along(d)`; bonus linear in the size symbol; exact worst case | `ing/2001` on a zone without a direction | ING-O-TOL-1 | 1 |
| Realized geometry | `realize:` fixes every noise symbol; names unchanged; PMI from nominal | Non-size sites listed in the report under `Mmc` and `Lmc` | ING-O-TOL-2 | 1 |
| GD&T attachment and dialects | Typed aspects, dialect modules, tombstones | `ing/42xx`, `ing/4302`, `InvalidControl` | MEC-O-TL-1, ING-O-TYPE-1 | 1 |
| `Approx<T>` | Budgets in `Pointwise` and `Goal` norms; outward rounding; property reads at a named basis | `ing/6104` | ING-O-TRUTH-1 | 1 |
| Decision rule | Disjoint enclosures decide under `decides_on`; Kleene logic; confidence; requested fidelity in keys | `Undecided { reason, needed }` | ING-O-TRUTH-1 | 1 |
| Undecided control flow | Cached `Undecided` value; ceiling changes reporting only | `DependencyUndecided`; `ing/6401` in the report | ING-O-TRUTH-2 | 1 |
| Approximate inputs | `Guaranteed` only; bound into `InputSensitivity` | `ing/6403` with two fixes | ING-O-TRUTH-1 | 1 |
## Geometry in the language

Geometry lives in Kiln, not in the program, so this section explains how code refers to it: by handle, by stable name and by query.

### Kiln-held values

`Body`, `Part`, `Assembly`, `Instance`, `InstanceSet`, `Field` and `Material` values are immutable handles to values that Kiln holds and the CAS (Crucible's content-addressed store) keeps. Code calls operations and std features that return new handles. Handle equality is content equality (`ObjectId`), and `a.same_geometry(b)` compares the name-free `GeometryId`s; MEC owns the Part and Assembly encodings.

| Type | Created by | Key members (std) |
| --- | --- | --- |
| `Body` | Operations and features; `+`, `-`, `&` | `faces`, `edges`, `regions`, `aspects`, `volume`, `bbox`, `mass_properties`, `convert(into:)` |
| `Part` | `part(body, name:, item:)` | `.body`, `.material(m)`, `.tolerance(target, control)`, `.require(…)`, `.csys(name)`; an unassigned material's property fails with `ing/6701` |
| `Assembly` | `assembly(instances, mates:)` | `.instances()`, `.find(path)`, `.bom()`, `.interference()` |
| `Instance` | `instance(part_or_assembly, at:, fixed:)` | `.part`, `.placement`, `.csys(name)`, `.path` |
| `InstanceSet` | `instances(of:, at:, min:)` ("Assemblies, variants and families") | `.members()` keyed by anchor, `.member(key)`, `.count()` |
| `Field<D, V>` | Flux operations and std physics | Defined by FLX |

Each Boolean expression without intermediate bindings lowers to one n-ary `anvil::boolean`, so `base + web - pocket` rounds once. A bound intermediate, as in `let ab = a + b`, is its own node, because its binding has its own `CallSite` and entity names. The prelude defines `origin`, the directions `x`, `y` and `z`, the axes and the planes `plane.xy`, `plane.yz` and `plane.xz`. Reference geometry (`plane.offset`, `axis.of`, `point.on`) is MEC's `std::mech::refgeom`, anchored by queries.

### Call sites and names

A face keeps its name across edits only if its name comes from something an edit does not change. An `Entity<K>` is a Body's `ObjectId` plus an `EntityId`, valid only with its Body, and its accessors return `Approx` values. Anvil names entities by `CallSite`, which Ingot derives from source text alone ([contract section 5.5](../contract.md#55-geometry-and-product-structure)). A `CallSite` is the path of call frames from the Evaluation's root; each frame, a feature or `fn` call, has three parts.

| Part | Rule | Stable under |
| --- | --- | --- |
| Statement | A `let` is (item path, arm path, binding name); an unnamed statement is (item path, arm path, preceding binding name, ordinal after it). Arm paths name `then`, `else` or a `match` pattern's canonical text | Edits elsewhere, moves, reformatting, literal edits, retyping |
| Call | The callee's name and its occurrence index among same-name calls in the statement | Calls of other names; a same-name call renames only later ones |
| Keys | One key per enclosing iteration ("Patterns, loops and keys") | Inserting or removing other elements |

Renaming a binding is a refactor that writes `#[was(original_name)]`, which keeps every entity name. The attribute always holds the original name, so a second rename rewrites it rather than stacking another. `crucible fmt --retire-was` removes every `#[was]` in one Proposal, whose review lists the entity renames and the checks, Waivers and Evidence records they touch; a major revision is the usual moment.

Live-session block ids never enter a `CallSite`: cloning, pushing or mirroring through any Git host and rebuilding leaves every `EntityId` unchanged. A same-name call inserted before others in one statement renames the later ones. The deny-by-default lint `ing/l-repeated-stage` flags a statement with several entity-naming calls of one name, and its fix splits the statement into bindings.

**Decision D-ING-21:** `CallSite`s derive from source text: frames of statement identities from binding names, call identities from callee name and occurrence, and iteration keys.
*Why:* identities must survive a Git round trip, a retyped statement and an appended stage, and only the text survives all three.
*Rejected:* editor block ids (they change on a Git round trip); slot paths (appending a stage renames every later one); source offsets; a per-call identity from a collaborative-editing data structure (not derivable from text).

Nothing in Ingot orders, numerically hashes or prints names. `Entity<K>` orders by Anvil's canonical geometric order, and `Seed::from(x)` hashes `x` with names removed, as label invariance requires.

A transform (`move`, `rotate`, `mirror`, `transform`) always keeps names. When one operation receives two operands carrying one `EntityId`, as a Boolean or a combine can, Anvil relabels the operand from the later transform in program order. Its entities take role `copy` or `mirror`, keyed by that transform's `CallSite`, and `copy(x)` relabels at once. `seed.face(role: top).copies()` follows copies on request, and a reflection marks its entities with the aspect `Mirrored` ([ANV, Copies and placements](02-anvil.md#copies-and-placements)).

### The query language

Positional indices break on the first topology change, so Ingot selects entities by what they are and where they came from. A `Query<K>` describes a selection on a subject Body and re-resolves wherever it is used. Methods on a Body, Part, Instance or query build it, and `Query<Point>` covers derived points such as `face.corners(inset:)`.

| Element | Syntax | Meaning |
| --- | --- | --- |
| Subject and count | `b.face(…)`, `b.faces(…)`, also `edge`, `vertex`, `region`, `aspect` | Singular needs one match; plural at least one unless `count:` says otherwise |
| Anchor | `part.face(base.face(role: end_cap))` | Descendants of the anchor through Anvil's lineage |
| Role | `role: end_cap`, `role: end(outline.top)`, `role: lateral(any)` | Entities created with that role, declared per entity kind with `#[roles(face: …, edge: …, vertex: …)]`; ANV owns std's vocabulary; a wrong-kind role fails with `ing/5002` |
| Creator, history | `created_by: holes`; `new`, `modified`, `all` | Entities from the call site that produced `holes`; created or modified by the subject's operation |
| Geometric filters | `normal: +z`, `kind: Cylinder`, `area: 100mm2..`, `radius: 2.95mm..=3.05mm`, `parallel_to:`, `within:` | Certified predicates; a `Tol` argument fails with `ing/4103`, so a selection never becomes a manufacturing tolerance |
| Topology | `.edges()` of a face query, `adjacent_to:`, `bounded_by:` | Adjacency in the subject |
| Rank selectors | `longest`, `largest`, `nearest: p`, `first(along: d)`, `last(along: d)` | Only after an anchor or role, else `ing/l-fragile-selector`. A winner whose margin is small against the spread of the candidates carries `Note::NearTie { runner_up, margin }` (ANV) |
| Set algebra | `q1 + q2`, `q1 - q2`, `q1 & q2` | On one subject |
| Custom filter | `where: \|f\| f.area() > 2 * hole_area` | A predicate under the decision rule: `Undecided` shows `Pending` below the ceiling and `ResolveError::Ambiguous { entities, needed }` at it |
| Extent use | `accept: [Merged, Partial, Fragile]`, default `[]` | For an extent use (an edge loop, a GD&T target), a merge, partial deletion, `Ordinal` id or near tie fails with a `ResolveError` unless accepted |

```
let bores  = body.faces(kind: Cylinder, radius: 2.95mm..=3.05mm, created_by: holes)
let rim    = top.edges() - top.edges(adjacent_to: bores)
let lip    = body.edge(created_by: base, role: lateral(any), last(along: +x))   // rank after a role
let blends = body.faces(new)
```

A query resolves on the Body of the operation that consumes it, mapping its selection through lineage, so `fillet(solid, base.face(role: end_cap).edges())` works. A `Query` parameter resolves on the first `Body` or `Part` parameter unless `#[on(param)]` names another. Each query lowers to a canonical `QueryPlan` that `anvil::resolve` evaluates as its own node, and a `ResolveError` arrives at the query's span with ranked fixes. ANV's sampled stability analysis reports `RankSwap` when a rank selection changes winner across declared parameter ranges.

There is no positional access (`ing/5001`). `.resolve()` returns entities in canonical geometric order, `sorted_by` in a stated order, and `e.query()` anchors a query on one entity's `EntityId`. Resolution never silently picks another entity at the evaluated configuration.

**Decision D-ING-8:** Queries are values resolved by a separate `anvil::resolve` node: certified declarative filters, rank selectors only after an anchor or role, and arbitrary predicates as `where:` closures under the decision rule.
*Why:* declarative filters can be certified, cached and explained, and one rule for every `Undecided` keeps queries consistent with branches.
*Rejected:* string selectors such as CadQuery's `">Z"`; positional slicing; unanchored ranks; a `where:` that fails at once on `Undecided` (it would disagree with `if`).

### Builder blocks and sketches

A sketch is a set of items, not a sequence of statements, so Ingot collects it with a block. A call may end with a block, as in `sketch(plane.xy) { outline }`; this is Swift's result-builder mechanism with a smaller rule [SE-0289]. A function opts in with a final `Builder<I, Ctx>` parameter, and each statement whose type implements `Emit<I>` contributes its items (`ing/2301` otherwise). A `let` names its items as result fields, so `let r = rect(…)` yields a `Sketch<{ r: Rect }>`.

`if`, `match` and `for` contribute their branches' or iterations' items, and a clash with an enclosing binding is `ing/1104`. ELX's `network { … }` uses the same mechanism with set-like accumulation.

Inside a sketch, entities are symbolic: `line(p0, p1)` creates unknown points seeded at `p0` and `p1`, accessors return `Expr<Length>`, and `e1 == e2` builds an `Equation` item. A helper's named sub-entity becomes the role argument of what is swept from it. `side(outline.top)` names the face an extrude sweeps from that edge, and `end(outline.top)` the edge it leaves on the end cap.

| Helper | Named sub-entities |
| --- | --- |
| `rect` | `left`, `right`, `bottom`, `top`, in the sketch frame |
| `slot` | `start_arc`, `end_arc`, `side_a`, `side_b` |
| `polygon` | `edge(k)`, keyed from a declared start vertex |

```
sketch(plane.xy) {
    let top = line(point(-10mm, 3mm), point(10mm, 3mm))          // seeds
    horizontal(top)
    dim(top.length, 40mm)
    chord_ratio(fan, 0.8) == 0mm                                  // an Equation item
}
pub fn chord_ratio(a: Arc, k: Real) -> Length { a.chord_length - k * 2 * a.radius }
```

`chord_ratio`, an ordinary function over `Length`, accepts `Expr<Length>` because quantity parameters accept every flavor. Branching on a symbolic value fails with `ing/2402`, and `select(cond, x, y)` builds conditional residuals. Local Newton solves use `local_solve(residual, x0)`, differentiated by the implicit function theorem at the converged point.

An `Expr<T>` lowers to `kernels::expr`, Crucible's one hash-consed symbolic expression type, which FLX owns. The kernel IR, FLX's intermediate form for every numeric kernel that affects results, compiles from it ([contract section 7.5](../contract.md#75-shared-kernel-ir-and-symbolic-expressions)). Sketch constraints, analytic Fields, weak forms and residuals therefore share one representation and one symbolic differentiation, and equal expressions hash equal.

**Decision D-ING-9:** Constraints, analytic Field expressions and weak forms are one mechanism: staged symbolic values built by ordinary functions and lowered to the shared expression type `kernels::expr`.
*Why:* one mechanism serves MEC's constraints, FLX's constitutive functions and analytic Fields, and equal expressions become equal keys.
*Rejected:* a `constraint` keyword with its own subset; tracing code into the kernel IR (captures one branch); a language-private expression graph beside Flux's and Anvil's (three implementations of one idea).

`anvil::solve_constraints` solves a sketch block as one node. A solved point is an `Approx<Point3>`, `Guaranteed` when Anvil's Krawczyk test (an interval test that proves one root in a box) succeeds for its block, and `Estimated` otherwise. Under-determined blocks are proved through their minimum-displacement KKT system (ANV, MEC). SketchGraphs offers "15 million sketches extracted from real-world CAD models" [SketchGraphs], and an oracle converts a fixed sample into sketch blocks.

Sketch seeds are inline literals rounded to MEC's quantum, and a build never warm-starts from an earlier solve ([MEC, Determinism and seeds](06-mechanical.md#determinism-and-seeds)). Ingot owns how a drag writes them back. A released sketch drag rounds the seeds in decimal millimetres and writes only entities that moved by more than the quantum. Before writing, the edit re-solves from the rounded seeds and checks that branch qualifiers and solution agree within the certified bound; otherwise it writes more digits.

**Decision D-ING-26:** A sketch drag writes back only the seeds that moved by more than MEC's quantum, after re-solving from the rounded values, and concurrent edits to the seeds of one under-determined block conflict.
*Why:* seeds decide under-determined sketches, so a written seed must reproduce the solution the person saw, and a drag that moved nothing must change no text.
*Rejected:* writing every seed of the block (needless textual conflicts); writing without re-solving (a rounded seed can pick another branch); merging concurrent seed edits by last writer (one solution from two intents).

### Assemblies, variants and families

An assembly's structure must be knowable without evaluating every variant, so Ingot restricts what decides whether an Instance exists. An Instance's path lists instance names from the root (`drive/wheel`). A query through an Instance carries its placement, and mates take `CoordSys` values (MEC). A record marked `#[interface]` derives a `compatible(a, b)` check.

Variants are enum or record parameters marked `#[configuration]` on assembly features ([contract section 6](../contract.md#6-ingot-syntax-reference)). Conditional regions that depend only on configuration parameters and constants are variant regions, whose Instances carry the region's condition. An Instance or Instance set under any other condition fails with `ing/2601`, so Kiln computes the 150% BOM, the bill of materials over every variant, by abstract interpretation (KLN).

An Instance set separates existence from multiplicity. `instances(of: f, at: anchors)` places one member per anchor of a keyed list, typically a resolved query, as one BOM line whose existence follows the static rule. Members, count and per-member parameters are evaluated and keyed by anchor, so a new hole changes a quantity, not the BOM's structure.

```
let screws = instances(at: cover.aspects(created_by: bolt_holes), of: |h| iso4762(m6, length: grip(h)))
```

A set is empty only if it declares `min: 0`; otherwise an empty set fails with `ing/6203 EmptyInstanceSet`. Mates and interference address members by key, and MEC's `fasten` returns a set.

**Decision D-ING-22:** Existence of an Instance or Instance set depends only on `#[configuration]` parameters and constants, checked at compile time; a set's members and count may depend on any value.
*Why:* the 150% BOM needs static existence, and one fastener per resolved hole needs a computed count.
*Rejected:* `options` and `when` keywords; enumerating configurations (exponential); a configuration count checked against the holes (two edits per hole).

A shaft diameter drives a catalog bearing, the housing bore and a fit check:

```
use parts::acme::deep_groove_ball as bearing_62xx            // illustrative catalog package

pub record DriveParams { shaft_d: Length = 12mm, load: Force = 400N, speed: AngularVelocity = 3000rpm }

pub feature drive_unit(p: DriveParams = DriveParams {}) -> Assembly {
    let brg = bearing_62xx(bore: p.shaft_d)?            // a CatalogSelection over pinned definitions
    let seat = fit(p.shaft_d, k6)
    let h = instance(bearing_housing(bore: fit(brg.outer_d, H7), width: brg.width), fixed: true)
    let s = instance(stepped_shaft(d: seat, length: 80mm))
    let b = instance(brg.part)
    assembly([h, s, b], mates: [fastened(b.csys("outer"), h.csys("bore")),
                                fastened(b.csys("inner"), s.csys("seat")),
                                revolute(s.csys("axis"), h.csys("axis"))])
    .require(brg.basic_dynamic_rating > 10 * p.load, name: "bearing_capacity")
    .require(brg.limiting_speed > 1.2 * p.speed, name: "bearing_speed")
    .require((seat - brg.bore_tol).upper() <= 25um, name: "max_interference")
}
```

A `CatalogSelection` is a pure function over pinned definitions, plus pinned offers when it ranks by price or stock (ELX); `crucible update parts` refreshes only the pins. `?` turns `NoCatalogMatch` into a failure whose fixes are the nearest candidates, and editing `speed` re-evaluates only `bearing_speed`. Exported at `realize: Mid`, the housing bore and the shaft seat sit at the centres of H7 and k6.

A feature's parameter list is a record type, `Params<f>`, and a call spreads a record into named arguments. A design table is a table of parameter records, which MEC's families use ([MEC, Derived parts and families](06-mechanical.md#derived-parts-and-families)):

```
let b = bracket(..heavy, width: 90mm)                     // later arguments override the spread
pub let brackets = family(bracket, key: |r| r.item, rows: table {
    item     | width | thickness     | load
    "BR-060" | 60mm  | 6mm ± 0.1mm   | 1.2kN
})
```

A row's type is `{ item: String, ..Params<bracket> }`. `table("brackets.csv")` reads a repository file whose header names units (`width [mm]`), and a mismatched cell fails with `ing/3501 UnitMismatch { column, expected }`. Onshape configures a part through small per-input tables rather than one large design table [Onshape configurations]; Ingot's typed records give the same small tables, with units checked.

### Patterns, loops and keys

A pattern is a feature whose instances differ only in their keys, and a `for` loop yields a list. Iteration contributes keys, never positions:

- iteration over entity lists or resolved queries keys by `EntityId`;
- MEC's generators return keyed lists (`linear` by `(i, j)`, `circular` by angular index, `at_points` by anchor, and so on);
- integer ranges and literal lists keep integer keys, and `keyed(xs, by: f)` keys any list, failing with `ing/6202 DuplicateKey` on a repeat;
- `ing/l-positional-key` warns when a computed list whose length depends on geometry is iterated by position.

Pattern `skip:` lists take keys (MEC). `fold` and `scan` carry running state, since there is no mutable accumulator.

```
let vents  = pattern(vent_slot(length: 10mm), at: linear(dir: +x, count: 8, spacing: 6mm))
let graded = for i in 0..8 { vent_slot(length: 10mm + i * 2mm) |> move(x: i * 6mm) }
```

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Kiln-held values and Booleans | Handles compared by `ObjectId`, geometry by `GeometryId`; one n-ary Boolean per expression without intermediate bindings | `ing/6701` | ING-O-EXEC-1 | 0 |
| Text-derived `CallSite` | Frames of statement, call and keys; `#[was]` holds the original name; `--retire-was` | `ing/1102`; `ing/l-repeated-stage` | ING-O-NAME-1, ANV-O-SITE-1 | 0 |
| Label invariance in the language | No order, numeric hash or printing of names; name-free seeds | None: the language cannot express a violation | ANV-O-LABEL-1 | 0 |
| Copies and placements | Transforms keep names; colliding operands relabelled in program order | None: cannot fail; Anvil relabels | ANV-O-COPY-1 | 1 |
| Queries | Canonical plans resolved by `anvil::resolve`; anchored ranks; `accept:` for extent uses; kinded roles | `ResolveError`; `ing/4103`, `ing/5001`, `ing/5002` | ING-O-QUERY-1, ANV-O-NAME-2 | 1 |
| Builder blocks and sketches | `Builder<I, Ctx>`; symbolic entities lowered to `kernels::expr`; certified solved points; seed write-back | `ing/1104`, `ing/2301`, `ing/2402` | ING-O-TYPE-1, ING-O-EDIT-1, ING-O-SKETCH-1, ANV-O-SOLVE-1 | 1 |
| Variant regions | Instance existence from configuration parameters and constants only | `ing/2601` | ING-O-ASM-1 | 1 |
| Instance sets | Static existence; evaluated members keyed by anchors; `min: 0` | `ing/2601`; `ing/6203` | ING-O-ASM-1 | 2 |
| Catalog selections | Pure over pinned data; re-resolve on argument change | `NoCatalogMatch` with candidates | ING-O-KILN-1 | 2 |
| Families and tables | Record spread, table literals, CSV with unit headers | `ing/2105`, `ing/3501` | MEC-O-PF-12 | 1 |
| Keyed iteration | Keys from entities, generators, ranges and `keyed` | `ing/6202`; `ing/l-positional-key` | ING-O-NAME-2 | 1 |
## Evaluation

A design must rebuild the same way everywhere and re-run only what an edit touches, and the evaluation rules below make both true.

### Calls and effects

Every Ingot call is pure. Calls differ in cost and in whether Kiln memoizes them, and their declarations say which. A `feature` may return any type and is the unit of history and caching; a `fn` is not.

| Call kind | Declared with | Kiln node |
| --- | --- | --- |
| Function | `fn` | None; the executor calls it directly |
| Memoized function | `#[memo] fn` | Keyed by code hash and arguments only; may not call operations or features (`ing/2501`) |
| Feature | `feature` | Feature node, keyed with its `CallSite` and requested fidelity |
| Operation | `extern fn` with `#[op("anvil::blend")]` | Op node keyed by its `NodeKey` ([contract section 7.2](../contract.md#72-keys-failures-and-aborts)) |
| Wasm component export | `extern fn` with `#[component(…)]` | Op node whose implementation is the Wasm component |
| External Op | `extern fn` with `#[external(…)]`, declared by its package (ECO) | Op node on untrusted-evaluation workers ([contract section 7.8](../contract.md#78-trust-and-the-shared-cache)) |
| Query resolution | Implicit where a `Query` reaches an operation | Resolve node |
| Check | `require` | Check node |

Operations, Wasm component exports and External Ops are the only engine effects: pure in meaning, expensive, asynchronous and cached. `ingot-bindgen` generates `std::ops::anvil` and `std::ops::flux` from the operations catalogs, and any package may write `extern` declarations checked against them (`ing/8001`). Source never names a behavior version; `ingot.lock` pins one per operation.

std chooses each helper's kind by one rule, which the lint `ing/l-feature-kind` checks. A helper that calls an entity-naming operation or returns `EntityId`s is a `feature`. A pure helper estimated above 10⁶ steps is a `#[memo] fn`, and any other is a `fn`.

**Decision D-ING-10:** Ingot has no user-visible effect system: operations are pure calls, and side channels (checks, notes, tolerance sites, PMI) are write-only accumulators in canonical call-site order, as in Salsa [Salsa].
*Why:* effect annotations would describe effects the language forbids, and canonical order makes accumulators independent of evaluation order.
*Rejected:* effect rows (nothing to track); threading a context and an id through every call, as FeatureScript does (boilerplate).

### Determinism and randomness

[Contract section 7.3](../contract.md#73-determinism) owns the determinism rules, PLT the mechanisms, and KLN the random-stream keys. Ingot adds these language rules:

- strict left-to-right evaluation, checked `Int` overflow, and no NaN or infinity values (`ing/6102`);
- ordered maps and sets, stable sorts, and no `Real` map keys (`q.key(resolution: 1um)` quantizes);
- NFC strings without locale; nothing ordered or hashed by name; labels invisible to code, since Kiln joins them;
- no time, environment, files or network: sources, tables, Assets and External inputs are Kiln input cells read by content.

Randomness is a value. `Rng` keys Philox-4×32-10, Salmon and colleagues' counter-based generator, which carries three rounds of safety margin [Salmon 2011]. The n-th number is a pure function of key and n, so streams split and run in parallel without changing any value.

```
let rng = Rng::new(seed).split("pins")                 // seed: an explicit parameter, never ambient
let u = rng.uniforms(count, of: 0.0..1.0)
```

std's samplers (`sobol`, `latin_hypercube`, `normal`) take an `Rng`. `Seed::from(x)` hashes `x` without names (a Body by `GeometryId`), so MEC's scramble seeds stay label-invariant, and `rng.seed()` passes a 64-bit seed to a Wasm component.

### Failures and Aborts

A `Failure` is a deterministic, typed value that says why a computation produced no result: a fillet radius too large, a query split, `OpVersionRetired`. KLN owns how failures are cached and how Aborts propagate ([KLN, Failures and Aborts](05-kiln-repo-plm.md#failures-and-aborts)); Ingot owns how code sees them.

A failure propagates to the nearest `try`, which turns it into `Result<T, Failure>`, or becomes the enclosing feature call's result. Dependents that need the value fail with `DependencyFailed { upstream }`.

```
let rounded = match try body |> fillet(edges, r) {
    ok(b) => b,
    err(BlendError::RadiusTooLarge { max }) => body |> fillet(edges, 0.95 * max),
    err(e) => fail(e),
}
```

`Failure` is an extensible union, like OCaml's extensible variants [OCaml extensible variants]. Every enum implementing `Error` adds its variants, and a match over `Failure` needs a wildcard arm. An `Undecided` value from control flow is not a `Failure`, and `try` cannot catch it.

An Abort is environmental: cancellation, resource or budget exhaustion, device or worker loss, or Kiln's evaluation-wide limits. No Ingot construct can observe one, so a fallback can never be taken because a worker ran out of memory.

**Decision D-ING-11:** `try` catches only `Failure`s; no Ingot construct observes an Abort, and a failure propagates to the nearest `try` or feature boundary.
*Why:* `?` on every geometry call is noise, and a branch that could see an Abort would make an environmental accident part of the design.
*Rejected:* `Result` on every operation; untyped exceptions; a `try` that catches every kind of stop.

A feature's checks are evaluated against its result; when the feature fails, they report `Error(DependencyFailed)`. A failure inside one Instance never erases sibling work.

### Limits

Per-call limits are counted in units the language defines, with the cost table in the language behavior version. Each limit ends in a `Failure` from KLN's catalog of limit outcomes.

| Limit | Unit | Default per feature call | Failure |
| --- | --- | --- | --- |
| Fuel | Steps of the cost table | 10⁹; `#[fuel(…)]` raises it up to the manifest maximum | `kiln/fuel_exhausted` |
| Call depth | Ingot frames | 2,048 | `kiln/stack_exhausted` |
| Memory | Semantic bytes: 8 per scalar or handle, 16 per collection header | 1 GiB | `kiln/memory_limit` |
| Operation calls | Count | 10⁶ | `kiln/work_limit { kind: OperationCalls }` |
| Symbolic expression size | Expression nodes | 10⁷ | `kiln/work_limit { kind: ExpressionSize }` |

A call's steps include the plain functions it calls, while feature and `#[memo]` calls are nodes with their own limits. An outcome therefore never depends on the caller's remaining budget or on the cache. An operation call charges 100 steps plus 1 per marshalled element. Effective limits come from source and manifest only and enter the node key.

Kiln adds two evaluation-wide limits as Aborts. Nested demands stop at 10,000, so `f(n) = f(n + 1)` aborts with `DemandDepthExhausted`, and a per-Evaluation fuel governor ends in `BudgetExhausted`. An organization ceiling below a requested limit refuses the Evaluation at admission with `FuelCeilingExceeded`, and a host out of memory raises `ResourceExhausted`.

**Decision D-ING-23:** Per-call limits come from source and manifest only and enter the node key; evaluation-wide limits and policy ceilings act only as Aborts.
*Why:* a policy-clamped limit would make two organizations cache different results for one key, and per-call limits alone allow unbounded chains of nodes.
*Rejected:* ceilings inside the limit; per-call limits as the only bound; wall-clock limits (nondeterministic).

`#[suppressed]` on a `let` removes the call: a pipeline statement whose input and output types agree binds its input, and other uses fail with `ing/6601 Suppressed`. Rollback is the request `EvalRequest { target, until: statement }`, never a source edit.

### The Ingot IR and Kiln

Lowering produces the Ingot IR (IIR), a dataflow graph in the style of the RVSDG, whose "regions capture the hierarchical structure of programs" [Reissmann RVSDG]. Ingot is pure, so the IIR has no state edges.

| IIR construct | Meaning |
| --- | --- |
| Simple node; Kiln call node | Plain computation; an Op, resolve, feature or check call with its `CallSite` |
| γ, map and fold, λ and φ regions | Conditionals; loops carrying keys; functions and recursive groups |
| Observation edge | Where the executor needs a Kiln-held value's content |

Spans live in a side table, so an edit above a function leaves its IIR unchanged. Each module's code hash is a SHA-256 Merkle hash over its IIR and the code hashes of the modules it uses.

1. **Front-end nodes.** A module's front end is keyed by its source hash, the language behavior version and its imports' interface hashes. Its outputs are the IIR, identified by the module code hash, and diagnostics, also keyed by the compiler release. Releases emit bit-identical IIR for one language behavior version, so IIR is shared across releases. Its stages backdate, so a comment edit stops at the IIR.
2. **Feature nodes.** A feature call's key follows contract section 7.2, with its `CallSite`, its requested fidelity and its effective limits. Its value splits into outputs with their own change markers: the result, one per accumulator kind, and metadata (fuel, cost). Metadata never enters backdating, so a fuel-only edit re-executes nothing downstream.
3. **Asynchronous calls.** The executor issues each Kiln call, receives a pending handle at once and suspends only at observation edges. Independent calls therefore run in parallel, and Kiln prefetches calls known before any observation.
4. **Program order.** Each call records its program-order index. When several calls fail, the outcome is the earliest in program order, and speculative work after it never changes a result. Anvil's copy relabelling reads the same index.
5. **Overrides.** A request may carry literal overrides keyed by `LiteralSite`, a `CallSite` plus an argument slot. Kiln treats them as input cells, and a node's key includes the overrides in its own code. Results computed under drag overrides never enter the shared cache (KLN), and a wrongly typed override fails with `ing/6502`.

Drags stream overrides through AGT's `edit.stream` and `evaluate.subscribe`, on PLT's `Drag` pool lane. An override's `LiteralSite` follows `#[was]`, so a concurrent rename of the binding keeps the drag alive; only deleting the literal ends the drag, with a notice (UIX).

When a drag starts on a literal, Ingot compiles a residual program over the literal's forward slice, with everything else constant. Its outputs equal the full program's, so a drag frame pays only for what the literal reaches.

[[DIAGRAM diagrams/01-ingot-pipeline.jsx: Ingot pipeline · front end, executor and Kiln]]

Read the diagram left to right: the front end turns source into IIR, the interpreter hands each call to Kiln as a pending handle, and values return at observation edges.

### Derivatives and edit plans

A drag in the viewport must change the right literal, and derivatives tell UIX which one. They also serve Flux's `grad(J, wrt: [p1, p2])`. Data dependence plus provenance gives the literals that can affect an entity, exactly and cheaply. Forward mode uses dual numbers and each Op's tangent rule, and reverse mode uses Kiln's `Differentiable` operations (KLN); an Op without a rule fails with `NotDifferentiable { op }`.

In phase 1, edit plans rank by provenance first: the literal of the call whose `CallSite` and role created the dragged entity. IIR dependence distance comes next, and derivatives refine the ranking from phase 2, when `anvil::shape_velocity` lands.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Calls and accumulators | Eight call kinds; canonical accumulators as separate outputs | `ing/2501`, `ing/8001`; `ing/l-feature-kind` | ING-O-KILN-1 | 0 |
| Determinism and randomness | Bit-identical values, failures and fuel; keyed Philox streams | None: cannot fail; Aborts are never cached | ING-O-EXEC-1, ING-O-EXEC-2 | 0 |
| Failures and Aborts | `try` catches `Failure` only; no construct observes an Abort | Typed `Failure`; `DependencyFailed` | ING-O-EXEC-1, ING-O-EXEC-4 | 0 |
| Per-call limits in keys | Limits from source and manifest; ceilings at admission | KLN's limit `Failure`s; Abort `FuelCeilingExceeded` | ING-O-EXEC-5, ING-O-EXEC-2 | 0 |
| Evaluation-wide limits | Demand depth and fuel governor as Aborts (KLN) | Abort `DemandDepthExhausted` | ING-O-EXEC-4 | 0 |
| IIR and the Kiln contract | Front-end keys; IIR shared across releases; split outputs; pending handles; program order; requested fidelity in keys | `DependencyFailed` | ING-O-EXEC-1, ING-O-KILN-1, ING-O-CHECK-1 | 0 |
| Literal overrides | Keyed by `LiteralSite`; never in the shared cache; follow `#[was]` | `ing/6502` | ING-O-EDIT-2 | 1 |
| Suppression and rollback | Binding takes the pipeline input; rollback as a request | `ing/6601` | ING-O-EDIT-1 | 1 |
| Drag specialization | Residual program on the forward slice | None: falls back to full evaluation | ING-O-EDIT-2 | 1 |
| Derivatives | Dependence and provenance ranking (1); forward and reverse modes (2) | `NotDifferentiable { op }` | ING-O-DERIV-1 | 1, 2 |

## Diagnostics and checks

A design language earns trust through its errors and its checks, so both share one structure that the UI, the CLI and agents read.

### Diagnostics

Compile-time diagnostics and evaluation failures share one record.

```rust
pub struct Diagnostic {
    pub code: Code,                        // "ing/3001"; other families use their own prefixes
    pub severity: Severity,                // base's one enum: Error | Warning | Info | Hint
    pub message: String,                   // one sentence: what is wrong and why
    pub primary: SourceSpan,
    pub labels: Vec<(SourceSpan, String)>, // secondary spans
    pub notes: Vec<String>,                // the rule, linked to its catalog page
    pub fixes: Vec<Fix>,                   // ranked
}
pub struct Fix { pub title: String, pub edits: Vec<SourcePatch>, pub applicability: Applicability }
pub struct SourcePatch { pub path: SourcePath, pub range: TextRange, pub expected: Sha256, pub replacement: String }
```

`Applicability` is `MachineApplicable`, `MaybeIncorrect` or `HasPlaceholders`, and `SourcePatch` is the record AGT's edit methods take. Every code renders as `<family>/<code>` ([contract section 7.6](../contract.md#the-api-and-its-principals)): Ingot's numbered errors are `ing/<number>`, its lints `ing/l-<name>`, and "Diagnostic codes" in the Reference lists the families. Query fixes carry Anvil's sampled stability results (ANV).

Every code has a generated catalog page with a triggering example and each fix, compiled in CI. A `MachineApplicable` fix must compile and remove its diagnostic. The canonical example's unit error reads:

```
error[ing/3001]: cannot add Length and Force
  --> bracket.ingot:14:17
14 |     let x = width + load
   |             ----- ^ ---- Force (kg·m/s²), declared at 11:5
   |             Length (m), declared at 9:5
   = fix (maybe incorrect): convert load with a compliance: `width + load * compliance`
   = fix (has placeholders): compare instead: `width < ?`
```

An evaluation `Failure` adds the feature call chain, the entities involved and an optional cause. Anvil's and MEC's fixes arrive as `Fix` values naming the design's own bindings, and the interpreter reports the exact failing expression.

### Checks

`require` declares a check: a predicate with a severity, a fidelity, the weakest bound kind that may decide it, a name and a source. It never changes the value it attaches to, and it runs as a separate node after the geometry it reads.

```
require stress < 0.6 * sy, severity: Error, fidelity: SignOff, decides_on: Estimated,
        name: "static_margin", because: "allowable of 0.6 Sy for this bracket class"
part.require(part.mass() < 120g, severity: Warning)       // attaches to the Part and returns it
```

| Field | Default | Meaning |
| --- | --- | --- |
| `severity` | `Error` | `Error`, `Warning` or `Info`; only an `Error` check can block a gate, and `Hint` fails with `ing/2001` |
| `fidelity` | `SignOff` | The fidelity a gate evaluates; a lower one makes the outcome provisional |
| `decides_on` | `Estimated` | The weakest bound kind that may decide: `Estimated` or `Guaranteed` |
| `name` | none | Part of the `CheckId`; required on `Error` checks by `ing/l-unnamed-check` |
| `because` | none | Rationale for reports and agents |

A check's identity is its `CheckId`: the attachment's `CallSite` or Instance path, plus its `name`. The deny-by-default lint `ing/l-unnamed-check` requires a name on every `Error`-severity check. Its machine-applicable fix derives one from the predicate's left operand, such as `von_mises_max`, and the GUI's "Add a check" writes the name itself. Inserting or removing another check therefore never changes a named check's identity, its verdict history, its Evidence records or its Waivers.

A lower-severity check without a name falls back to the `require` statement's identity. A `CheckId` never derives from predicate text, so editing a limit keeps its history. A check declared twice on one attachment fails with `ing/1103`, whose fix adds `name:`.

A `require` statement attaches to its feature call, a module-level one to the design, and `x.require(…)` to `x`, under the Instance path in assemblies. A comparison chain records value, limit and margin, and a conjunction records one sub-outcome per conjunct.

The outcome is the `CheckOutcome` of [contract section 5.6](../contract.md#56-physics-evaluation-and-checks). Its verdict is `Pass`, `Fail`, `Undecided { reason, needed }`, `Error(Failure)` or `Skipped { reason }`, and it records its confidence, its Evidence records and the policy allowances it read.

A policy allowance is a record in a policy package pinned in `ingot.lock`, such as a design code's partial factor that the code says covers model uncertainty. A check reads allowances like any pinned input, so they enter its trace and its key. The model-form part of the budget is then `Quantified` by the allowance or stays `NotQuantified`, and the one decision rule gives `Pass`, `Fail` or `Undecided { Unquantified }`. Nothing re-evaluates a check after the fact.

ING owns the gate predicate, which KLN and AGT apply at protected merges, Proposals and releases. A check meets a gate when its severity is below `Error`, or its verdict is a non-provisional `Pass` in a platform class the gate accepts, or a Waiver covers it. "Provisional" means only that the outcome's fidelity is below the check's declared one.

A `require` under the protected `oracles/` directory has the source `Protected(path)`, which agents cannot edit; every other check has `Declared(span)`. `#[waive(reason:, until:)]` on a `require` statement, or with `check:` naming a full `CheckId`, only requests a Waiver. It counts nowhere until an authorized person signs a matching Waiver record ([contract section 5.4](../contract.md#54-signature-records-and-the-signature-table)). Agents may write the attribute, never the record, and `Protected` checks accept none.

When no study estimates a check's functional, the language service offers a visible fix that adds it to the study's `goals:` (FLX).

The bracket's check shows the verdicts at work. The check holds at 0.6 × 240 MPa = 144 MPa, the conservative end of the basis interval in COV's 6061-T6 record ([COV, The bracket's check](04-coverage.md#the-brackets-check)); the stresses are illustrative.

| Situation | Outcome of `static_margin` |
| --- | --- |
| `Preview` result | `Undecided { Indicator }` |
| `Interactive`, 6 mm: 96 MPa ± 12 MPa `Estimated`; model form `NotQuantified` | `Undecided { Unquantified([ModelForm]) }`; the margin to the limit still shows |
| `SignOff`, 6 mm: 94 MPa ± 1.5 MPa, confirmed by one refinement; a pinned policy allowance quantifies model form | `Pass` at confidence 0.99, meeting the gate |
| `SignOff`, 6 mm, after validation against GP1's strain-gauged proof loads makes the model-form part `Estimated` | `Pass` with no allowance |
| `SignOff`, 4 mm: about 210 MPa at the web-root fillet | `Fail` |
| The refinement's value falls outside the first bound | `Undecided { CalibrationUnconfirmed }` |
| The peak lies on the boundary of an excluded neighbourhood | `Undecided { MaximumAtExclusion }`, with the fix "model the support" |
| The solve does not converge | `Error(failure)`, with the solver's diagnostics |

**Decision D-ING-12:** Checks are declarations evaluated as separate nodes: a failing or undecided check never stops geometry, and no feature branches on a check's outcome.
*Why:* designers need to see failing geometry, expensive predicates run later at lower priority, and adding a check never changes a design or a solve.
*Rejected:* aborting assertions (they hide the geometry); checks as Booleans in the dataflow (they could alter geometry).

### Free text

Text can carry instructions to a later reader, human or agent, so Ingot separates text from structure. The lossless tree classifies every span as free text or structure. Comments, string literals, description templates, and identifiers that neither the compiler produced nor a person typed in Crucible's editor are free text. `repo` records the integrity of the context that wrote each span (KLN).

A string evaluated from a free-text span of untrusted integrity is an `ExternalText` value, written `external("…")` in source. It carries its span's integrity and origin and is never read as instructions. How that integrity reaches node labels is [contract section 5.3](../contract.md#53-labels)'s rule. `api` returns every `ExternalText` as a handle, and only a per-span endorsement, which shows the text verbatim, makes free text trusted.

**Decision D-ING-24:** Every span is free text or structure; merging endorses only structure, and values evaluated from untrusted free text are `ExternalText`.
*Why:* an agent could address a later reader through a merged comment or a literal evaluated into a part name, and integrity on nodes would taint every result downstream of one untrusted name.
*Rejected:* wrapping only imported strings; banning agent comments (they document intent); integrity on spans only (evaluated strings would lose it); integrity joined into node labels (one untrusted name taints all geometry).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Diagnostics and fixes | One structure; one `Severity`; `<family>/<code>` codes; ranked `SourcePatch` fixes; catalog pages | None: a failing machine-applicable fix is a compiler defect | ING-O-DIAG-1 | 0 |
| `require` and outcomes | `CheckOutcome`; named `CheckId`s; allowances read as pinned inputs; protected sources | `Error(Failure)`; `Undecided`; `ing/1103`; `ing/l-unnamed-check` | ING-O-TRUTH-1, ING-O-CHECK-1 | 1 |
| Gate predicate | Severity, a non-provisional `Pass` in an accepted platform class, or a Waiver record | Gate refused with the failing checks | ING-O-CHECK-2 | 1 |
| Check independence | Adding, removing or inserting a check changes no other node's key or `CheckId` | None: cannot fail | ING-O-CHECK-1 | 1 |
| Free-text spans | Classified spans; `ExternalText` values for untrusted text; handles in `api` | `ing/0003` | ING-O-TEXT-1 | 1 |
## Execution

Phase 1 needs Ingot to orchestrate operations quickly on every target, not to compete with compiled numeric code, so one interpreter runs it everywhere until measurement says otherwise.

Until the code generator ships, the reference interpreter is the only Ingot executor on every target ([contract section 7.4](../contract.md#74-wasm-execution)). Written in Rust, it interprets the IIR in the canonical platform class with `detmath`, checking non-finite values, fuel and depth after every step. Heap frames let a call suspend without stack switching, and one interpreter per worker holds every suspended call in its own allocator region.

| Measure | Target | Benchmark |
| --- | --- | --- |
| Interpreter time per GP1 feature body, operations cached | ≤ 200 µs on the reference laptop; ≤ 600 µs in browsers | `ingot-bench` on GP1 |
| Ingot share of a golden-product rebuild | ≤ 2%, else the code generator enters | GP1 and GP2 rebuilds |
| Suspended feature calls | 500 within 256 MiB of the browser engine worker | Golden-product evaluations |
| Front-end re-check of an edited 2,000-line module | Under 30 ms | Edit-replay corpus |
| Drag residual program per frame, operations excluded | Under 1 ms | UIX drag scripts |
| Numeric Ingot against idiomatic Rust, once compiled | ≤ 2.5× natively; ≤ 4× in browsers | `ingot-bench` numeric programs |

All figures are targets. Until the code generator exists, heavy numeric loops go to operations or Wasm components.

**Decision D-ING-13:** The canonical-class interpreter is the only Ingot executor until `ingot-bench` shows Ingot above 2% of a golden-product rebuild; then a code generator to WebAssembly core modules enters, phase 2 at the earliest.
*Why:* phase 1 needs only orchestration speed, and a second executor would sit on the critical path with no gate that needs it.
*Rejected:* the code generator in phase 1; Cranelift native code (no browser path); Ingot to Rust (a run-time toolchain); LLVM (slow, no browser target).

The interpreter stays for cold start, debugging, replay and differential testing. The code generator emits one module per compilation unit with a source map, run by Wasmtime with Cranelift natively and by each browser's engine. Its modules pass the determinizer's verification, and the conformance oracle checks their fuel accounting.

Its optimizer never reassociates or contracts floating point, and it keeps every operation that can fail in program order. It charges fuel computed on the canonical IIR and never merges, duplicates or reorders Kiln calls. Suspension lowers to resumable state machines, since Wasmtime's tier documentation lists stack switching as unsupported by Cranelift on aarch64 [Wasmtime tiers].

Each worker keeps one instance with per-call allocator regions, and user modules take over from the interpreter at the next feature call boundary, unobservably.

**Decision D-ING-14:** Plain values use reference counting with in-place update of uniquely referenced lists and records, Perceus-style in the code generator.
*Why:* immutable, strict values are acyclic, Perceus is "garbage free" with "guaranteed in-place updates" [Reinking 2021], and prompt freeing keeps loops within the memory limit.
*Rejected:* a tracing collector (pauses in a drag frame); an arena per feature call (late freeing); ownership types for users (ceremony).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Reference interpreter | Canonical class; checks after every step; heap frames | Abort `ResourceExhausted` | ING-O-EXEC-1, ING-O-PERF-1, ING-O-PERF-2 | 0 |
| Code generator | Verified deterministic Wasm subset; state machines; Perceus | None: a rejected module is a compiler defect | ING-O-EXEC-1, ING-O-EXEC-3 | 2 at the earliest |

## Rust features and Wasm components

Some features need millions of steps per call or an existing Rust codebase, so a feature may be written in Rust and still look like Ingot to its callers.

When the tier rule of [contract section 4](../contract.md#4-layering-operations-wasm-components-features) says so, a feature is written in Rust as a Wasm component. `#[ingot::feature]` writes the WIT world (the WebAssembly Interface Types description of its imports and exports), the glue and a typed Ingot wrapper. A build fails if a checked-in artifact differs from its regeneration.

```rust
use ingot_sdk::{Angle, Body, Cx, Length, Plane};

/// Involute spur gear tooth profile, closed, centred on the origin.
#[ingot::feature(package = "acme::gears", category = "Power transmission", icon = "gear")]
pub async fn involute_profile(
    #[ingot(range = "0.1mm..=50mm")] module: Length,
    #[ingot(range = "6..=400")] teeth: u32,
    #[ingot(default = "20deg", range = "14.5deg..=30deg")] pressure_angle: Angle,
    cx: &mut Cx,                                                // the guest context
) -> Result<Body, GearError> {
    let mut s = cx.planar_builder(Plane::XY, "profile");       // the builder owns its call key
    for i in 0..teeth {
        let key = s.site_keyed("flank", i);                    // an owned key, so no second borrow of cx
        s.add_spline(key, &flank_points(module, pressure_angle, i)?)?;
    }
    s.finish_region().await.map_err(GearError::from)           // one crucible:ops call
}
```

`ingot-bindgen` generates the guest SDK, `ingot_sdk`, from the `crucible:ops` and `crucible:host` imports. Its `Cx` is the only context a `#[ingot::feature]` function receives. `OpCx` stays native-only, because it wraps runtime handles that an out-of-process component cannot hold (KLN, PLT).

| Method | WIT import | Failure |
| --- | --- | --- |
| `site(name)`, `site_keyed(name, key)` on `Cx` and on every builder | None; returns an owned call key appended to the call's `CallSite` | `ing/8201` on a duplicate key |
| Builders and operation calls (`planar_builder`, `anvil()`, `flux()`) | `crucible:ops/anvil`; `crucible:ops/flux` from phase 2; asynchronous | The operation's typed `Failure` |
| `seed()` | None; the call's `seed: u64` argument | None: cannot fail |
| `diagnostic(…)` | `crucible:host/diagnostics` | None: cannot fail |

`ingot-bindgen` emits `GearError` as an Ingot enum implementing `Error`, with the codes and fixes declared in Rust.

| Rule | Mechanism |
| --- | --- |
| A Wasm component call is an Op keyed by the determinized binary's hash, export and arguments | Pinned in `ingot.lock` (ECO) |
| Evaluation worlds import no WASI; randomness arrives only as a `seed: u64` argument from an `Rng` | [Contract section 7.4](../contract.md#74-wasm-execution) |
| Operation calls go through `crucible:ops` as recorded Op dependencies; engine data arrive only through handles from the inputs | [Contract section 4](../contract.md#4-layering-operations-wasm-components-features) |
| Every operation call and created entity takes a call key appended to the call's `CallSite`; duplicates fail with `ing/8201` | Stable `EntityId`s |
| Fuel is metered by the determinizer and limited by the wrapper's `fuel:` | Deterministic limits |
| Traps, `kiln/fuel_exhausted`, `kiln/stack_exhausted` and `kiln/memory_limit` are cached `Failure`s; host-caused growth failures and resource loss are Aborts | [Contract section 7.2](../contract.md#72-keys-failures-and-aborts) |
| Error estimates map to `Approx` values or `ErrorBudget` parts; `outside-envelope` maps to the validity flag | Wrapper convention |
| Diagnostics attach to the call's span in emission order; Wasm component strings become `ExternalText` | Write-only accumulator |
| The wrapper is the public interface; the raw `extern fn` is `pub(package)` | One typed signature |

A bare `f64` parameter becomes `Real` with `ing/8101`, asking for a unit alias in `ingot-bindgen.toml`; "WIT to Ingot" in the Reference lists the mapping. A Rust feature is an opaque debugger frame, and it has a forward derivative only when `#[ingot::feature(tangent = …)]` names an exported tangent. A package calls a Wasm component through the same generated binding, and the component's declared error estimate becomes a statistical `ErrorBudget` part, `Guaranteed` only if declared so.

**Decision D-ING-15:** `#[ingot::feature]` generates the WIT world, glue and typed Ingot wrapper from one Rust signature, whose function receives the generated guest context `ingot_sdk::Cx`.
*Why:* one signature carries units and ranges to the type checker and dialogs, and an out-of-process component needs a context made of imports.
*Rejected:* hand-written WIT and wrappers (drift); native Rust plugins (unsafe, no browsers); passing the native `OpCx` (it holds runtime handles a sandboxed component cannot have).

### Ingot values in Rust

Stable Rust cannot compute `Quantity<D1·D2>` from const generics, and Ingot creates kinds, records and domains at run time. The Rust form of an Ingot value therefore cannot be a compile-time generic. The erased forms are canonical ([contract section 5](../contract.md#5-core-cross-subsystem-types)):

- `Value`, an enum over scalars, `DynQuantity { si: f64, dim: Dim }`, records, lists and handles, where `Dim` is a vector of rational exponents over the eight base dimensions plus a kind id;
- `DynField { domain, value, header, repr }`, whose descriptors FLX owns.

Kiln memoizes these forms, the CAS encodes them and `crucible:ops` carries them.

Typed views are generated, never hand-written. `base` generates newtypes such as `Length`, `Stress` and `Torque`, with the `Mul` and `Div` impls the prelude's kind table lists. It also generates `Field<D, V>` as a checked view over `DynField`, through `TryFrom<DynField>`. `ingot_sdk` re-exports these views, so dimensions survive in Rust and every conversion checks. Rust code never uses `uom` or `typenum`.

**Decision D-ING-29:** In Rust, Ingot values have one erased canonical form, `Value` with `DynQuantity` and `DynField`, and typed views generated from the prelude's kind table.
*Why:* the strong angular system needs rational exponents and kinds that stable Rust generics cannot compute, and run-time records and domains need one representation that Kiln, the CAS and `crucible:ops` share.
*Rejected:* `uom` or `typenum` marker types (integer exponents, no kinds); hand-written newtypes per tab (drift from the kind table); `PhantomData`-typed Fields as the stored form (run-time domains have no Rust type).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `#[ingot::feature]` | One Rust signature generates WIT, glue and wrapper | Artifact drift fails the build; `ing/8xxx` | ING-O-RUST-1 | 1 |
| Guest SDK | `ingot_sdk::Cx` generated from the WIT imports; owned call keys; asynchronous operation calls | `ing/8201`; typed `Failure`s | ING-O-RUST-1 | 1 |
| Wasm component calls | Ops keyed per contract section 7.2; call keys; metered fuel | Typed `Failure`s; Aborts | ING-O-EXEC-1, ING-O-RUST-1 | 1 |
| Binding generation | WIT to Ingot with units | `ing/8101`, `ing/8102` | ING-O-RUST-1 | 1 |
| Rust representation | Erased `Value`, `DynQuantity` and `DynField`; generated typed views | `TryFrom` failure naming expected and actual dimensions | ING-O-RUST-1, ING-O-UNIT-1 | 0 |

## Packages and versions

Designs reuse features from other packages, so Ingot defines what a package is, what breaks it, and how an old design rebuilds identically years later.

A package is a directory with `ingot.toml` and modules under `src/`, rooted at `src/lib.ingot`. A design repository's root is `src/main.ingot`, whose `pub` items are its outputs. Items are private, package-wide with `pub(package)`, or public with `pub` and part of the semantic-version interface.

A `use` path starts with a dependency, `package`, `self` or `super`. Imports are acyclic (`ing/1301`), as in KCL [Zoo KCL modules], and two globs supplying one name are ambiguous (`ing/1201`).

```toml
[package]
name = "acme::gears"            # namespace::name; namespaces are registry-owned (ECO)
version = "1.2.0"
edition = "2027"
gdt-dialect = "asme"

[dependencies]
"std::mech" = "1"

[language]
display = { Length = "mm", Stress = "MPa" }
fuel = { default = 1e9, max = 1e11 }   # per feature call; enters node keys
```

The registry refuses a minor or patch release that breaks the public interface (ECO), and Ingot defines "breaks":

| Change | Release |
| --- | --- |
| Remove or rename a public item, parameter, field, role or coordinate system; change a parameter's dimension, kind or type; add an undefaulted parameter; narrow a range; extend an exhaustive enum | Major |
| Change a default value, or the entity names a public feature produces on the package's test designs | Minor, labelled output-changing (ECO) |
| Add a defaulted parameter, an item, a role or a variant to a `#[non_exhaustive]` enum; widen a range | Minor |
| Change test-design outputs through private code, keeping entity names | Patch, labelled output-changing (ECO) |
| Change only documentation, metadata or private code, leaving outputs and names unchanged | Patch |

`ingot.lock` is sorted TOML written only by tools. ING owns its `[language]` table: the language behavior version, which fixes evaluation semantics, the IIR lowering, the cost table, the n-ary Boolean rule and std numerics. `[operations]` pins operation versions (KLN and the owners), and `[[package]]`, `[[asset]]`, `[[external]]` and `[[evidence]]` pin the rest by SHA-256 (ECO, KLN). Compiler releases may change diagnostics and speed, never IIR, values, failures or fuel.

**Decision D-ING-16:** The lockfile pins a language behavior version beside the operation versions, and a toolchain implements every language behavior version in its support window.
*Why:* an old design must rebuild identically, and fuel costs and std numerics are part of its result.
*Rejected:* pinning the toolchain release (old toolchains kept runnable forever); letting editions carry behavior (ECO forbids it).

Resolution uses PubGrub, which can "explain errors more clearly than the alternatives" [PubGrub], through ECO's resolver; `ing/7001` carries its derivation and relaxations as fixes. The `pubgrub` crate is MPL-2.0, so ECO either links it under the MPL duties of [contract section 7.7](../contract.md#77-interop-ecosystem-and-support) or reimplements the algorithm. Two major versions of a package may coexist, and passing a value between them fails with `ing/7201`.

A module (one file) is the unit of a source label. A person who may not read a labelled module sees it only through its derived views, such as its signature. Each view has its own declassification record and is evaluated on cleared workers ([contract section 7.1](../contract.md#repo-plm-and-trust)). Front ends read only their imports' signatures, so the signature view is enough to compile against the module; nothing that joins an undeclassified output becomes readable.

Editions follow Rust's model: they change surface syntax, the prelude and lint defaults, never behavior. `crucible migrate` applies machine-applicable fixes and rejects any item whose IIR changes beyond spans. Rust's guide notes that "Cargo's automatic migrations aren't perfect" [Rust editions], and the IIR check makes Ingot's exact.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Modules and visibility | Three levels; acyclic imports; labelled modules seen through derived views | `ing/12xx`, `ing/1301` | ING-O-TYPE-1 | 1 |
| Semantic-version rules | The table above, including entity-name changes | Publish refused (ECO) | ING-O-PKG-1 | 1 |
| Lockfile and behavior versions | `[language]` pinned; releases never change IIR or values | None: a changed value is a compiler defect | ING-O-EXEC-1, ING-O-PKG-1 | 1 |
| Resolution | PubGrub with explanations; two majors coexist | `ing/7001`, `ing/7201` | ING-O-PKG-1 | 1 |
| Editions and migrations | IIR-preserving rewrites only | Non-preserving rewrites listed, not applied | ING-O-PKG-2 | 2 |

## Feature metadata and dialogs

A feature's signature already says what its parameters are, so it also generates the feature's dialog, documentation page and agent tool schema; attributes only refine them.

| Source element | Generated UI |
| --- | --- |
| Quantity parameter | Numeric field with unit, accepting expressions (UIX) |
| `Tol<T>` parameter, or a toleranced default | Value field with a tolerance sub-field |
| `Bool`; `enum` | Toggle; segmented control up to five variants, else a dropdown |
| `Query<K>` | Selection field showing the query, filtered by `K` |
| `Material`, catalog part types | Pickers bound to the material library and the catalog |
| `Option<T>`, record, `[T]` | Enable toggle; group; list editor |
| `in` range; doc comment | Field and slider bounds checked at evaluation (`ing/6501`); help text |

| Attribute | Meaning |
| --- | --- |
| `#[toolbox(category:, icon:, handles:)]` | Toolbox placement, icon and manipulator handles (UIX handle kinds) |
| `#[ui(group:, advanced, visible_if:, step:, filter:, label:)]` | Grouping, disclosure, visibility, slider step, selection filter, label |
| `#[roles(…)]`, `#[realizes(…)]`, `#[fuel(…)]`, `#[example]` | Created roles per entity kind; realized tolerance parameters; a raised fuel limit; a compiled, evaluated doc example |
| `#[deprecated(since:, instead:)]`, `#[removed(in:, instead:)]` | Lifecycle with fixes |

`visible_if` takes a pure closure over the parameter record, evaluated by the interpreter as values change. FeatureScript expresses the same with `if` statements in a `precondition` block [Onshape FeatureScript UI].

**Decision D-ING-17:** Dialogs are generated from signatures, types, doc comments and a small attribute vocabulary; there is no dialog language.
*Why:* one declaration serves dialog, docs, semantic-version checks and tool schemas without drift, and Onshape shows that generated dialogs work at scale.
*Rejected:* FeatureScript-style precondition blocks (a second statement language); hand-built dialogs (drift).

`crucible doc` generates reference pages; every `///` code block compiles, and `#[example]` blocks evaluate in CI with their checks. A public item without a doc comment fails the registry's coverage gate (ECO).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Dialogs from signatures | Types and attributes to fields, groups, handles and visibility | `ing/6501` out of range | ING-O-META-1 | 1 |
| Documentation | Compiled and evaluated examples; coverage gate | Publish refused (ECO) | ING-O-META-1 | 1 |

## Tooling

Agents, the GUI and people all edit Ingot as text, so its tools decide whether those edits stay small, mergeable and safe.

### Lossless tree and blocks

`ingot-syntax` parses into a lossless green-red tree in rust-analyzer's design, with the `rowan` crate [rowan]. Every byte belongs to exactly one block, because `repo`'s `MergeDriver` merges branches and live sessions block by block (KLN).

| Block | Head | Children |
| --- | --- | --- |
| File; item | Inner attributes; attributes, docs and signature | Top-level items; members, with the closing brace as tail |
| Parameter, field, variant; table row | The whole text | None |
| Statement; arm | Text up to the first nested block; the arm's opener | Arms; statements, with the closer as tail |

Comments belong to the block that follows them, and order-insensitive lists (`use` lists, named arguments, record fields) merge as sets. Parsing is block-local: each block parses under its own production, and an error stays inside it as `ERROR` nodes. A block broken by a concurrent edit keeps its kind and position, so "the last good result for that block" is well defined.

Statement order matters only for definition before use and for the ordinals of unnamed statements. The `MergeDriver` checks both after a merge, live or on a branch, and turns a violation into `Conflict::Text` on the block (KLN).

**Decision D-ING-18:** The grammar serves structural editing: newline-terminated statements, one statement per block, comments owned by the next block, named arguments merged as sets, atomic literals, block-local parsing.
*Why:* one block merge serves branches and live sessions, and it needs a block per unit of concurrent work and an owner for every byte; file-level recovery re-associated blocks after an error.
*Rejected:* a projectional editor (reviews and agents use text); semicolons with free layout (two diffs for one change); file-level error recovery.

Data modules, such as ELX's `Schematic` and `Layout`, are `table { … }` literals whose rows are atomic blocks. A row-specialized lexer skips the general tree and builds lossless nodes lazily when a row is edited. The target is 10⁶ rows parsed and hashed in under 1 s natively, measured in phase 2 before ELX needs it. If it is missed, the module splits by board region.

**Decision D-ING-27:** Data modules stay Ingot text, with no binary sidecar.
*Why:* merge, live sessions, span provenance, `CallSite`s and Git storage all work on text, and a second format needs a second path for each.
*Rejected:* a binary sidecar keyed by statement identity; a data format per subsystem.

### Formatting and structural edits

`crucible fmt` produces one idempotent layout per block: 100 columns, 4-space indents, one argument or pipeline stage per line when broken, alignment only in tables. Every GUI action and agent edit becomes the smallest `SourcePatch` list the formatter leaves unchanged:

| Action | Minimal source edit |
| --- | --- |
| Change a dialog value; drag a dimension | Replace one literal token, keeping its unit; drags replace the literal UIX's edit plan chose |
| Drag a sketch entity | Rewrite the seeds that moved by more than MEC's quantum; a drag that moves nothing writes nothing |
| Edit a driving dimension on a drawing | Replace the literal it traces to by provenance, else offer ranked edit plans; driven dimensions are read-only (MEC) |
| Add a feature | Insert one statement after the anchor, binding a fresh name derived from the feature (`fillet_2`) |
| Delete or reorder a feature | Remove or move one statement block with its comments, refused if a binding would precede its definition |
| Suppress; set a tolerance | Toggle `#[suppressed]`; rewrite `4mm` to `4mm ± 0.1mm` |
| Rename a binding | Rename every use and write `#[was(original_name)]` unless the binding already has one |
| Add a check | Insert a named `require` statement, or attach `.require(…, name:)` to a single-expression body |

### Language service and tools

Code-CAD users already work in their own editors, so the language service meets them there without letting an editor speak for the person. It implements LSP 3.17 (the Language Server Protocol) semantics in `ingot-service` [LSP 3.17]. The UI and agents reach it through `api`, and it also runs over stdio with first-party VS Code and Zed extensions. A custom request, `crucible/reveal`, drives Crucible's viewport from those editors; the in-app code panel is UIX's.

It offers pull diagnostics with evaluation failures, semantic tokens for units and roles, hover with values and bounds, and inlay hints for dimensions and flavors. Every fix is a code action, and a source map links each `EntityId` to its creating `CallSite` and span. Unfinished code becomes typed holes that evaluate to `ing/6001 Incomplete`, and evaluation proceeds around them as in Hazel [Omar typed holes]. Targets: completion and hover within 50 ms, diagnostics for an edited 2,000-line module within 100 ms.

A language-server connection cannot tell a person's keystrokes from an AI extension's writes. Spans arriving through it are therefore `data_untrusted` until the person confirms the batch on the approval origin. Only Crucible's own editor records a span as typed by a person ([contract section 7.1](../contract.md#repo-plm-and-trust)). The CLI and the editor extensions authenticate as a device agent, never as the person. They cannot merge, endorse, waive or export on the person's behalf ([contract section 7.6](../contract.md#the-api-and-its-principals)).

**Decision D-ING-25:** In phase 1 the language service ships inside Crucible and over stdio with VS Code and Zed extensions, plus a viewport request; text from external editors is untrusted until confirmed.
*Why:* code-CAD users already work in those editors, an in-app editor alone would compete with them, and an editor extension must not be a way for an agent to write trusted text.
*Rejected:* the in-app panel as the only editor; external editors without cross-probing; trusting language-server edits as typed by the person.

| Tool | Behavior | Phase |
| --- | --- | --- |
| Debugger | Replays a feature call in the interpreter from cached operation results, so stepping never recomputes geometry; DAP (the Debug Adapter Protocol) with `stepBack` and `reverseContinue` [DAP]; Bodies coloured by creating `CallSite` | 2 |
| REPL and notebooks | Cells compile as modules importing earlier cells; `.ingot` files with `//% cell` markers; outputs never saved | 2 |
| Tests | `#[test]`, `#[test(golden)]` comparing `ObjectId`s, `#[test(property, cases:)]` with seeded parameters; `assert_close` passes only on enclosures; failures shrink to a reproducible call | 1 |
| Benchmarks | `#[bench]` reports deterministic fuel and wall time; CI tracks fuel exactly and time statistically; `ops: cached` or `ops: cold` | 1 |
| KCL importer | KCL programs to Ingot with explicit units, in `io/` | 3 |

Tests are deterministic, so a flaky test is an engine defect.

**Decision D-ING-19:** Crucible builds Ingot from scratch and does not fork KCL's MIT-licensed implementation, studying its tests and documentation with attribution.
*Why:* most of Ingot is new, and `kcl-lib` couples execution to an engine connection that cloning its `ExecutorContext` shares [kcl-lib docs].
*Rejected:* forking `kcl-lib` (it would be rewritten anyway, and it carries default units); KCL source compatibility (conflicts with compile-time units); a KCL importer in phase 1 (no gate needs it).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Lexing and parsing | Every byte round-trips; malformed input becomes `ERROR` nodes inside its block | `ing/0xxx` with the expected tokens; never a crash or hang | ING-O-SYN-1, ING-O-SYN-2, ING-O-SYN-3 | 0 |
| Hidden-character rejection | Bidirectional, zero-width and tag characters only as escapes | `ing/0003` with an escape fix | ING-O-TEXT-1 | 0 |
| Unique statement names | One `let` name per block | `ing/1102` with a rename fix | ING-O-TYPE-1 | 0 |
| Lossless tree and block-local parsing | Every byte in one block; errors stay inside it | `ERROR` nodes; never a crash | ING-O-SYN-1, ING-O-SYN-3 | 0 |
| Data modules | `table` rows as atomic blocks; row lexer; 10⁶ rows under 1 s (target) | A missed target splits the module by region | ING-O-PERF-3 | 2 |
| Formatter and structural edits | Canonical, minimal, comment- and name-preserving; seed and drawing edits; `--retire-was` | Refused edits explain why | ING-O-EDIT-1 | 1 |
| Language service | LSP 3.17 in-app and over stdio; viewport request; external spans untrusted until confirmed | Degrades to plain text editing | ING-O-TOOL-2 | 1 |
| Holes | Evaluation around holes | `ing/6001` | ING-O-TOOL-1 | 1 |
| Debugger | Replay from cache; reverse stepping | None: a frame whose result left the cache is recomputed before stepping | ING-O-TOOL-3 | 2 |
| REPL and notebooks | Cells as modules; outputs from Kiln | Cell diagnostics as for modules | ING-O-TYPE-1 | 2 |
| Tests and benchmarks | Geometric assertions; golden and property tests; fuel tracking | Deterministic failures | ING-O-EXEC-1, ING-O-PERF-1 | 1 |
| KCL importer | KCL programs to Ingot with explicit units | Unmapped constructs listed | ING-O-TOOL-4 | 3 |
## Reference

### Crates and ownership

| ING owns | Others own |
| --- | --- |
| Syntax, grammar, formatting, editions | Operation semantics and behavior versions (ANV, FLX) |
| Types: `Quantity<D>`, `Tol<T>`, `Approx<T>`, `Truth`, `Expr<T>`, `CheckId`, `CheckOutcome`, `CallSite`, `LiteralSite` | `ErrorBound`, `ErrorBudget` (`base`, FLX); `Field` and `kernels::expr` (FLX) |
| Query syntax and lowering; the decision rule for `Truth`; the gate predicate; `realize:` | `EntityId`, lineage and `anvil::resolve` (ANV); aspect kinds and GD&T records (MEC) |
| Evaluation semantics, `Failure` and `Abort` as the language sees them, per-call limits | Scheduling, caching, labels, failure and Abort propagation, evaluation-wide limits (KLN); determinism mechanisms (PLT) |
| The interpreter, the Ingot IR and the deferred code generator | The kernel IR (FLX, `kernels`); the determinizer (PLT) |
| Diagnostics, fixes and check semantics | Policy packages, policy allowances and Waiver records (KLN); the verifier and `api` (AGT) |
| Modules, manifest language keys, lockfile `[language]`, semantic-version rules | Registry and signing (ECO); lockfile storage and merge (KLN) |
| `#[ingot::feature]`, the guest SDK, WIT bindings and the kind table that generates Rust views | WIT worlds and capabilities (ECO); `base`'s generated types (KLN, with every type owner) |
| Feature metadata, language service, debugger, tests | Dialog rendering and code panel (UIX); agent tools (AGT) |

| Crate (contract section 12) | Contents | Phase |
| --- | --- | --- |
| `ingot-syntax` | Lexer, block-local parser, lossless tree, formatter, edition migrations | 0 |
| `ingot-types` | Name resolution, inference, dimension and tolerance algebra, diagnostics catalog, the prelude kind table | 0 |
| `ingot-ir` | Ingot IR (IIR), lowering, `CallSite`s, the reference interpreter, differentiation | 0 |
| `ingot-bindgen`, `ingot-macros` | WIT bindings, the generated guest SDK `ingot_sdk`, `#[ingot::feature]` | 1 |
| `ingot-service` | Language server, structural edits, test runner; debugger and notebooks | 1; 2 |
| `ingot-codegen` | IIR to WebAssembly, entering only when justified ("Execution") | 2 at the earliest |

Every Ingot crate is `forbid(unsafe_code)`. `rowan` and Salsa are linked under their permissive licences; `pubgrub` is linked through ECO under MPL-2.0 duties or reimplemented ([contract section 7.7](../contract.md#adopt-port-or-study)).

### Source text

| Aspect | Rule |
| --- | --- |
| Encoding | UTF-8 in NFC (Unicode Normalization Form C), normalized by the platform layer on load; non-NFC input that bypassed it fails with `ing/0002` |
| Hidden characters | Bidirectional controls, zero-width characters and Unicode tag characters are rejected anywhere in source (`ing/0003`); string literals write them as escapes such as `\u{200B}` |
| Line endings | LF; CRLF is accepted and normalized by the formatter |
| Identifiers | UAX #31 default identifiers (an `XID_Start` character, then `XID_Continue` characters), with `_` added to the start set as the standard allows [UAX 31]; `ing/l-mixed-script` flags mixed scripts |
| Case | `snake_case` for functions, features, variables, fields and modules; `PascalCase` for types, traits and enum variants; deny-by-default lint `ing/l-naming` |
| Statements | A newline ends a statement unless inside brackets, after a binary operator, `,` or `\|>`, or before a line starting with `.`, `\|>`, `else`, `and`, `or` or `±`. No semicolons |
| Comments | `//` and nesting `/* … */`; `///` documents the next item and `//!` the module, both CommonMark |
| Attributes | `#[name(args)]` on the next item, parameter, field or statement; `#![name(args)]` on the module |
| Keywords | `and`, `as`, `else`, `enum`, `extern`, `false`, `feature`, `fn`, `for`, `if`, `impl`, `in`, `let`, `match`, `not`, `or`, `pub`, `record`, `require`, `self`, `Self`, `trait`, `true`, `try`, `type`, `use`, `where` |
| Contextual keywords | `kind` at item position, `table` before `{`, `package` and `super` in paths |

There is no `while` and no `return`. `%` is the percent suffix, so remainders are the functions `rem` and `mod`.

### Grammar

The grammar is LL(1) after the lexer, except that `{` after an expression needs a second token to separate record literals, blocks and builder blocks. A builder block follows only a call's closing parenthesis and needs parentheses in an `if`, `match` or `for` head.

```ebnf
file         = {inner_attr} {item} ;
item         = {attr} [visibility] (use_decl | fn_decl | feature_decl | extern_decl | record_decl
             | enum_decl | trait_decl | impl_decl | type_alias | kind_decl | let_decl) | require_stmt ;
attr         = "#[" path ["(" [arg {"," arg}] ")"] "]" ;
inner_attr   = "#![" path ["(" [arg {"," arg}] ")"] "]" ;
visibility   = "pub" ["(" "package" ")"] ;
use_decl     = "use" use_tree ;
use_tree     = path ["::" ("{" use_tree {"," use_tree} [","] "}" | "*")] ["as" ident] ;
path         = ident {"::" ident} ;
kind_decl    = "kind" ident ("=" | ":") dim_expr ;   (* "=" names a dimension; ":" a kind *)
fn_decl      = "fn" ident [generics] "(" [params] ")" "->" type [where_clause] block ;
feature_decl = "feature" ident [generics] "(" [params] ")" "->" type [where_clause] block ;
extern_decl  = "extern" ("fn" | "feature") ident [generics] "(" [params] ")" "->" type ;
params       = param {"," param} [","] ;
param        = {attr} ident ":" type ["in" expr] ["=" expr] ;   (* "in": checked range *)
record_decl  = "record" ident [generics] "{" [field_list] "}" ;
field_list   = field {"," field} [","] ;
field        = {attr} ident ":" type ["=" expr] ;
enum_decl    = "enum" ident [generics] "{" variant {"," variant} [","] "}" ;
variant      = {attr} ident ["(" type {"," type} ")" | "{" field_list "}"] ;
trait_decl   = "trait" ident [generics] [":" bounds] "{" {fn_sig | assoc_type} "}" ;
impl_decl    = "impl" [generics] [path "for"] type [where_clause] "{" {fn_decl | type_alias} "}" ;
fn_sig       = "fn" ident [generics] "(" [params] ")" "->" type [where_clause] ;
assoc_type   = "type" ident [":" bounds] ;
type_alias   = "type" ident [generics] "=" type ;
generics     = "<" ident [":" bounds] ["=" type] {"," ident [":" bounds] ["=" type]} ">" ;
bounds       = path ["<" type_arg {"," type_arg} ">"] {"+" path ["<" type_arg {"," type_arg} ">"]} ;
where_clause = "where" ident ":" bounds {"," ident ":" bounds} ;
let_decl     = "let" pattern [":" type] "=" expr ;

type         = path ["<" type_arg {"," type_arg} ">"] | "[" type "]" | "(" [type {"," type}] ")"
             | "{" field_types "}" | "fn" "(" [type {"," type}] ")" "->" type | "impl" bounds ;
field_types  = (ident ":" type | ".." type) {"," (ident ":" type | ".." type)} [","] ;
type_arg     = type | dim_expr ;
dim_expr     = dim_term {("*" | "/") dim_term} ;
dim_term     = (ident | "1" | "(" dim_expr ")") ["^" rational] ;
rational     = ["-"] int_lit | "(" ["-"] int_lit "/" int_lit ")" ;

block        = "{" {stmt} [expr] "}" ;
stmt         = {attr} (let_decl | require_stmt | expr) ;
require_stmt = "require" expr {"," ident ":" expr} ;
expr         = pipe ;
pipe         = range_expr {"|>" postfix} ;   (* right side must be a call *)
range_expr   = or_expr [(".." | "..=") [or_expr]] | (".." | "..=") or_expr ;
or_expr      = and_expr {"or" and_expr} ;
and_expr     = not_expr {"and" not_expr} ;
not_expr     = ["not"] cmp_expr ;
cmp_expr     = tol_expr {("==" | "!=" | "<" | "<=" | ">" | ">=" | "in") tol_expr} ;
tol_expr     = add_expr ["±" (add_expr | "(" add_expr "," add_expr ")")] ;
add_expr     = mul_expr {("+" | "-") mul_expr} ;
mul_expr     = unary {("*" | "/" | "&") unary} ;
unary        = ["-" | "+"] power ;
power        = postfix ["^" unary] ;   (* right-associative; -x^2 = -(x^2) *)
postfix      = primary {"." (ident | "require") [call_args [block]] | call_args [block]
             | "[" expr "]" | "?"} ;
call_args    = "(" [arg {"," arg} [","]] ")" ;
arg          = [ident ":"] expr | ".." expr ;   (* ..record spreads named arguments *)
primary      = literal | path | "(" expr {"," expr} ")" | "[" [expr {"," expr}] "]" | record_lit
             | map_lit | table_lit | if_expr | match_expr | for_expr | lambda | "try" expr | block ;
lambda       = "|" [ident [":" type] {"," ident [":" type]}] "|" expr ;
record_lit   = path "{" [fields] "}" | "{" fields "}" ;
fields       = (".." expr | ident ":" expr) {"," (".." expr | ident ":" expr)} [","] ;
map_lit      = "[" expr "=>" expr {"," expr "=>" expr} [","] "]" ;
table_lit    = "table" "{" ident {"|" ident} {row} "}" ;
row          = expr {"|" expr} ;   (* one row per line *)
literal      = int_lit | real_lit | quantity_lit | percent_lit | string_lit | "true" | "false" ;
quantity_lit = (int_lit | real_lit) (unit | "[" unit_expr "]") ;
unit_expr    = unit_term {("*" | "/") unit_term} ;
unit_term    = (unit | "(" unit_expr ")") ["^" rational] ;
pattern      = "_" | ident | literal | range_pat | path ["(" pattern {"," pattern} ")"]
             | path "{" ident [":" pattern] {"," ident [":" pattern]} ["," ".."] "}"
             | "(" pattern {"," pattern} ")" | pattern "|" pattern ;
range_pat    = literal (".." | "..=") [literal] | (".." | "..=") literal ;
if_expr      = "if" expr block ["else" (if_expr | block)] ;
match_expr   = "match" expr "{" {pattern ["if" expr] "=>" expr ","} "}" ;
for_expr     = "for" pattern "in" expr block ;
```

Precedence, loosest first: `|>`; ranges; `or`; `and`; `not`; comparisons (chainable); `±`; `+` and `-`; `*`, `/` and `&`; unary minus; `^`; postfix. On Bodies and sets, `+`, `-` and `&` are union, difference and intersection. `x |> f(a)` means `f(x, a)`, methods come only from `impl` blocks and traits, and a call followed by a block passes it as a builder.

Named arguments may appear anywhere, and positional arguments fill the remaining parameters in order; `ing/l-name-arguments` asks for names after the second. Within one block each `let` name is unique (`ing/1102`), so every statement has a stable textual name. There is no ad hoc overloading: one name has one signature.

### Diagnostic codes

| Codes | Area | Examples |
| --- | --- | --- |
| `ing/0xxx` | Lexing and parsing | `ing/0002` non-NFC source; `ing/0003` hidden characters; `ing/0201` unknown unit |
| `ing/1xxx` | Names and modules | `ing/1001` unknown name; `ing/1102` duplicate binding; `ing/1103` duplicate check identity; `ing/1104` builder name clash |
| `ing/2xxx` | Types and traits | `ing/2001` mismatch; `ing/2402` branch on a symbolic value; `ing/2601` Instance or Instance set under a computed condition |
| `ing/3xxx` | Units and kinds | `ing/3001` dimensions; `ing/3002` kinds; `ing/3201` affine misuse; `ing/3501` unit mismatch in a table |
| `ing/4xxx` | Tolerances and GD&T | `ing/4101` comparison of tolerances; `ing/4103` tolerance in a query filter; `ing/4104` tolerance not realized; `ing/4201` material condition on a non-size aspect |
| `ing/5xxx` | Geometry references | `ing/5001` positional entity access; `ing/5002` role on the wrong entity kind |
| `ing/6xxx` | Evaluation failures | `ing/6001` incomplete code; `ing/6203` empty Instance set; `ing/6401` undecided branch |
| `ing/7xxx` | Packages and lockfile | `ing/7001` unresolvable dependency; `ing/7201` value across major versions |
| `ing/8xxx` | Bindings | `ing/8001` extern signature differs from the catalog; `ing/8201` duplicate call key |
| `ing/l-<name>` | Lints | `ing/l-fragile-selector`, `ing/l-repeated-stage`, `ing/l-hertz-phase`, `ing/l-shared-symbol`, `ing/l-tolerance-dropped`, `ing/l-unnamed-check`, `ing/l-feature-kind`, `ing/l-positional-key` |

### WIT to Ingot

| WIT | Ingot |
| --- | --- |
| `bool`, `s8` to `s64`, `u8` to `u32`; `u64` | `Bool`, `Int`; `u64` fails with `ing/6101` above 2⁶³ − 1 |
| A `u64` named `seed`; a `fidelity` enum | `Seed`; omitted and filled by the host |
| `f32`, `f64`; `crucible:units` aliases | `Real`; `Length`, `Force`, `Temperature` (kelvin, converted in the wrapper) |
| `string`, `list`, `option`, `result`, `tuple` | `ExternalText` for Wasm component strings; `[T]`, `Option`, `Result`, tuples |
| `record`, `variant`, `enum`, `flags` | `record`, `enum`, `enum`, `Set<Enum>` |
| Body and Field resources; other resources | `Body`, `Field<D, V>` handles; opaque handles owned by the wrapper |

## State of the art

The design languages Ingot is measured against: Zoo's KCL, Onshape's FeatureScript, the Python libraries CadQuery and build123d, and OpenSCAD. KCL's documentation gives `10in * 25.4` as `254in` [Zoo KCL units], and FeatureScript threads `context` and `id` through every call [Onshape FeatureScript library]; Ingot's types and dataflow remove both. Figures below are targets on contract section 13.3's reference laptop.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Units and dimensions | Units-of-measure inference (F#); kinds and affine points (mp-units, after ISO 80000) | F# units of measure; mp-units; Pint | Rational dimensions, kinds, strong angular system, erased at run time | ING-O-UNIT-1; check time under 5% of front-end time |
| Tolerance arithmetic | Affine arithmetic (Comba and Stolfi; de Figueiredo and Stolfi); GUM and Supplement 1 | Sigmetrix CETOL 6σ (3D tolerance analysis in CAD) | Affine forms per site and realizing feature; exact coverage; name-free order; realized geometry | ING-O-TOL-1, ING-O-TOL-2 |
| Approximate comparisons | Interval enclosures with three-valued logic | FLX's budgets | One decision rule over `ErrorBudget`s; allowances as pinned inputs | ING-O-TRUTH-1 |
| Entity naming | Provenance with history (`Select.NEW`; `qCreatedBy`) | Onshape FeatureScript | Text-derived `CallSite`s, keyed iteration, anchored queries | ING-O-NAME-1, ING-O-NAME-2, ANV-O-NAME-2 |
| Incremental compilation | Red-green memoization with early cutoff (Salsa) | rust-analyzer | Salsa-style stages inside Kiln; split node outputs | ING-O-KILN-1; re-check under 30 ms |
| Execution | Compiled code "an order of magnitude faster than interpretation" [Xu and Kjolstad]; Cranelift within about 14% of LLVM [Cranelift]; browsers 45% to 55% slower than native on SPEC [Jangda 2019] | V8, Wasmtime; wasmi with fuel | Interpreter now; Wasm code generator when justified | ING-O-PERF-1 |
| Memory in pure languages | Perceus reference counting with reuse (PLDI 2021) | Koka | Reference counting with in-place update; Perceus in the code generator | ING-O-PERF-2 |
| Deterministic execution | Wasm with fuel and canonical semantics (Wasmtime; Wasm 3.0 deterministic profile) | Wasmtime with NaN canonicalization | One canonical interpreter; verified modules | ING-O-EXEC-1 |
| Live programming | Typed holes with evaluation around them (Hazel) | Hazel | Holes from the error-resilient parser | ING-O-TOOL-1 |
| Bidirectional editing | Program repair from output edits (Sketch-n-Sketch) | Sketch-n-Sketch; Onshape dimension editing | Provenance ranking, then derivatives | UIX's intent-match rate |
| Lossless syntax trees | Red-green trees (Swift libsyntax, rust-analyzer) | rust-analyzer with `rowan` | `rowan`, block grammar, block-local parsing for the block merge | ING-O-SYN-1, ING-O-SYN-3, ING-O-PERF-3; 2,000 lines reparsed under 5 ms |
| Version resolution | PubGrub | uv | PubGrub through ECO's resolver | ING-O-PKG-1 |
| Language evolution | Editions with automated migration (Rust) | Cargo | Editions plus an IIR-equality check | ING-O-PKG-2 |
| Dialogs from code | FeatureScript preconditions | Onshape | Typed signatures plus attributes | ING-O-META-1 |
| Sketch language | Constraint graphs catalogued by SketchGraphs | Onshape's sketcher, SketchGraphs' source | Builder blocks of symbolic entities and `Equation` items | ING-O-SKETCH-1 |
| Debugging | DAP with `stepBack` and `reverseContinue` | rr (record, replay, reverse execution) | Replay from Kiln's cache, exact because evaluation is pure | ING-O-TOOL-3 |

| Capability | Incumbent and its documented feature | Crucible's capability row and phase | Standing |
| --- | --- | --- | --- |
| Features written in a language | Onshape: "Part Studios are written in FeatureScript", and std features' source is public [Onshape FeatureScript intro] | "Calls and accumulators"; "Calls and effects", phase 0 | Ahead: the same openness, with compile-time units and tolerances and pure, cached calls |
| Units in expressions | KCL numbers take a file's default unit [Zoo KCL units]; FeatureScript checks units at run time [Onshape FeatureScript variables] | "Dimensions and kinds", phase 0 | Ahead: units, kinds and affine temperatures are checked before anything runs |
| Configurations and design tables | Onshape configurations: list, checkbox and variable inputs, each in its own table [Onshape configurations] | "Variant regions" and "Families and tables", phase 1 | Equal on inputs; ahead in that variant existence is static, so KLN's 150% BOM (phase 3) needs no enumeration |
| Geometry at tolerance limits | Creo regenerates a model at the upper, middle, lower or nominal bound of each dimension [PTC Creo dimension bounds] | "Realized geometry", phase 1 | Ahead: adds maximum and least material condition and keeps every entity name and the nominal PMI |
| Tolerance stack analysis | CETOL 6σ, "3D model-based tolerance analysis software that integrates directly into leading CAD platforms" [Sigmetrix CETOL] | "Affine tolerance arithmetic" and "Geometric zones in stacks", phase 1; MEC's 3D zone path, phase 2 | Equal for one-dimensional stacks in phase 1, read straight from the design's own tolerances; Later for 3D zones |
| Robust references to faces and edges | FeatureScript queries by creating feature (`qCreatedBy`) [Onshape FeatureScript library]; KCL tags with an index fallback [Zoo KCL edge references]; build123d's `Select.NEW` [build123d selection] | "Queries" and "Text-derived `CallSite`", phases 0 and 1 | Ahead: no positional fallback, typed resolve errors with ranked fixes, names that survive Git round trips |
| Generated feature dialogs | FeatureScript preconditions generate the dialog [Onshape FeatureScript UI]; OpenSCAD's Customizer reads comments beside variables [OpenSCAD customizer] | "Dialogs from signatures", phase 1 | Equal, without a second statement language |
| Code-CAD in a general-purpose language | CadQuery and build123d are Python libraries [CadQuery intro] | The whole language, phases 0 and 1 | Ahead on purity, determinism and compile-time units; the Python ecosystem is Out of scope, reached through the Python SDK |
| Agent modelling through tools | SolidCraft, an AI-built clone, runs an MCP (Model Context Protocol) server for agents and saves a feature timeline as JSON [SolidCraft] | "Formatter and structural edits" and "Diagnostics and fixes", phases 0 and 1 | Ahead: agents edit a typed program whose changes review as text and whose errors carry fixes that compile |
| Where the model runs | KCL executes against an engine connection to Zoo's service [kcl-lib docs] | "Reference interpreter", phase 0 | Ahead: the same interpreter runs locally on every Tier 1 target and in browsers |

## Platform notes

| Platform | Note |
| --- | --- |
| Browsers | The wasm32 interpreter runs in the engine worker and yields at Kiln calls in single-threaded builds; large evaluations follow PLT's browser memory table |
| iPadOS (Tier 2) | No JIT is needed: the interpreter runs in the web build inside WebKit ([contract section 7.4](../contract.md#74-wasm-execution)) |
| Code generator in browsers | Core Wasm with 128-bit SIMD only; pages allow `'wasm-unsafe-eval'`, without which "WebAssembly is blocked" [MDN wasm-unsafe-eval] |

## Interfaces with other subsystems

| To | What | Types | Phase |
| --- | --- | --- | --- |
| KLN | Front-end stages with separate IIR and diagnostics; code hashes; split outputs; program order; overrides keyed by `LiteralSite`; limits and requested fidelity in keys; `CheckId`s and the gate predicate; block grammar and statement order for the `MergeDriver`; variant regions and Instance sets; cached `Undecided` values | `CallSite`, `LiteralSite`, `CheckId`, `CheckOutcome` | 0 |
| ANV | `CallSite`s; `QueryPlan`s with anchored ranks and `accept:` lists; kinded role filters; sketch helpers' sub-entities; program order for copy relabelling; one n-ary Boolean per expression; `InputSensitivity`; the `Truth` rule for filters | `Query`, `Tol<T>` | 0 |
| FLX | Product- and parameter-domain `Field` syntax; `Complex<Q>`, `.absolute()`, `select`; `Expr<T, Out>` lowered to `kernels::expr`; `Approx`, `Truth` and the decision rule; `goals:`, `wrt:` and `study.regular()` regions in checks | `Field<D, V>`, `Expr<T>`, `Approx<T>` | 1 |
| MEC | Features, builder blocks, symbolic constraints, seed write-back, families, `Tol<T>` with fits, forwarding and name-free order, `zone.along` contributions, `realize:`, typed aspect queries, keyed iteration, Instance sets, `#[configuration]` | `Feature`, `Tol<T>`, `InstanceSet` | 1 |
| MFG | `realize:` for exports; records, enums, `Map`, kinds for Field domains, `Decimal` and `Money<C>` with `round_minor`, `require` | `Quantity<D>`, `Tol<T>`, `CheckOutcome` | 1 |
| ELX | `network { … }` with set-like accumulation; port power checks; `Tol` correlation groups; `CatalogSelection`; `#[configuration]`; `#[interface]`; data modules as `table` rows | `Tol<T>`, `Network` | 1 |
| COV | Records, `Range` as interval, kinds for regime functions, `require`, the decision rule, property reads at a named basis | `Quantity<D>`, `CheckOutcome` | 1 |
| UIX | Language service; `EntityId`-to-span map; dialog metadata; overrides that follow `#[was]`; edit-plan ranking; minimal `SourcePatch`es, drawing dimensions included | `SourceSpan`, `Feature` | 1 |
| AGT | Diagnostics with `SourcePatch` fixes and `<family>/<code>` codes; the formatter; metadata and doc comments for tool schemas; `ExternalText` values; `CheckOutcome`s, the decision rule and the gate predicate | `CheckOutcome`, `Feature`, `ExternalText` | 1 |
| ECO | Manifest language keys; lockfile `[language]`; editions; semantic-version rules; binding, wrapper and guest SDK conventions | `Feature` | 1 |
| PLT | The interpreter on every target; generated modules for verification | `PlatformClass` | 0; 2 for generated modules |
| `base` (KLN and every type owner) | The prelude kind table from which typed Rust views are generated | `Value`, `DynQuantity` | 0 |

## Oracles

All oracles live under `oracles/ingot/`, which agents building Ingot cannot edit. The corpus is std, the golden products, every registry package's tests and a generated set of random well-typed programs.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| ING-O-BRK-1 | Contract section 6's example at 6 mm and 4 mm | Compiles; the check region contains the web-root fillet; `Pass` at 6 mm and `Fail` at 4 mm at `SignOff`, never `Undecided { SingularPoint }`; `width + load` gives `ing/3001` |
| ING-O-EXEC-1 | Conformance of the interpreter on every Tier 1 target and browser engine, and of compiled code, on values, failures, fuel and Kiln call sequences; IIR across compiler releases; `sum` against `det_sum` | Bit-identical on the corpus |
| ING-O-EXEC-2 | Deepest legal recursion on every target, and one deeper | Runs everywhere; fails with `kiln/stack_exhausted` everywhere |
| ING-O-EXEC-3 | Differential fuzzing of the code generator: interpreter against compiled code, optimized against unoptimized | No divergence per release |
| ING-O-EXEC-4 | `f(n) = f(n + 1)` on every Tier 1 target | Aborts with `DemandDepthExhausted`; no memo entry |
| ING-O-EXEC-5 | Evaluations under varied organization ceilings | One limit outcome per source and manifest; a lower ceiling aborts at admission |
| ING-O-SYN-1 | Parse then print, for valid and invalid inputs | Every byte reproduced |
| ING-O-SYN-2 | Parser fuzzing on arbitrary bytes | No crash, hang or unbounded memory in 10⁹ executions per release |
| ING-O-SYN-3 | Block-local parsing | Concatenated blocks reproduce the tree; a failing block keeps its kind and position |
| ING-O-UNIT-1 | Units: seeded dimension, kind, affine, degree-radian, rpm-hertz and hertz-phase errors, plus each RFC kind's error; at least 50 textbook rotational, electrical and thermal formulas; generated Rust views against the kind table | Every error rejected with its code or lint; every formula type-checks without casts; every generated view's `Mul` and `Div` match the table |
| ING-O-TYPE-1 | Typing judgments on a curated corpus; random well-typed programs; `Decimal` rounding | Expected judgments; zero internal type failures; round half to even on every product and quotient |
| ING-O-TOL-1 | Tolerances against exact rational stacks and 10⁶ samples per nonlinear case; symbols keyed by realizing feature; coverage against exact convolution; a 10⁵-site stack; statistics under re-randomized names; zone contributions with MMC bonus; `2 * thickness` passed to a realizing parameter | Exact linear stacks; containment otherwise; the canonical bracket has two independent thickness symbols; `.rss` within `.limits()`; identical bits after renaming; the hand-computed fixed-fastener margin; `ing/l-tolerance-dropped` fires |
| ING-O-TOL-2 | GP1 and the `drive_unit` example exported at `Mid`, `Mmc` and `Nominal` | Every fitted diameter at its mid-limit or material-condition limit; the same `EntityId`s as at `Nominal`; PMI identical to the nominal Evaluation's |
| ING-O-TRUTH-1 | Comparisons with injected bounds, kinds, envelopes, refinements, confidences and allowances; property reads at a basis | Never `True` or `False` against the exact relation; `Indicator` and unquantified parts never decide; allowances read are listed exactly; a basis read is exact and named in the report |
| ING-O-TRUTH-2 | Branches and `where:` filters on `Undecided`, under an `Interactive` ceiling, then a `SignOff` ceiling with warm caches | The second shows `Pending`, then the decided value; `ing/6401` and `ResolveError::Ambiguous` appear only in reports at the ceiling |
| ING-O-DIAG-1 | Machine-applicable fixes in the corpus | 100% compile and remove their diagnostic |
| ING-O-EDIT-1 | Recorded GUI sessions, sketch drags included | Minimal patches; comments and untouched `CallSite`s kept; a drag that moves nothing writes nothing; rounded seeds rebuild bit-identically |
| ING-O-EDIT-2 | Drag specialization and overrides on golden-product drag scripts | Residual and full programs bit-identical; an overridden result never answers a request without the override |
| ING-O-QUERY-1 | Query lowering and roles | Equal queries hash equal; unanchored ranks raise `ing/l-fragile-selector`; `Tol` filters fail; every role of every std sweeping feature resolves; a wrong-kind role fails with `ing/5002` |
| ING-O-KILN-1 | Minimal re-evaluation over 500 scripted edits (shared with KLN-O-MIN-1) | Re-executed nodes equal the reference set; none after fuel-only edits |
| ING-O-DERIV-1 | Derivatives on smooth programs; dependence sets; phase 1 ranking on drag scripts | Taylor order 2 ± 0.1; dependence exact; provenance literal ranked first |
| ING-O-RUST-1 | `#[ingot::feature]`, bindings, the guest SDK and every Rust block in this tab | Checked-in WIT and wrappers match regenerated ones; `ingot_sdk` matches the WIT imports; units match WIT aliases; every Rust block compiles with `rustc` against the generated `ingot_sdk` |
| ING-O-PKG-1 | Unsatisfiable dependency fixtures; two-major coexistence; semantic-version classification | Every failure explained; no silent choice; every change classified by the table |
| ING-O-PKG-2 | Edition migrations on the corpus | IIR and output hashes preserved |
| ING-O-META-1 | Metadata and examples | Every std feature has a dialog, docs and an evaluated example; this tab's examples evaluate |
| ING-O-TOOL-1 | Programs with random holes | Hole-independent bindings equal the complete program's |
| ING-O-TOOL-2 | Service latency on an edit-replay corpus, in-app and over stdio | Within the stated targets at p95 |
| ING-O-TOOL-3 | Debugger replay | Forward then backward steps give identical frames |
| ING-O-TOOL-4 | KCL sample programs through the importer | Each builds the reference geometry or lists unmapped constructs |
| ING-O-SKETCH-1 | A fixed SketchGraphs sample converted to sketch blocks | Every constraint type expressible; re-solves meet MEC-O-SK-1's target |
| ING-O-NAME-1 | Golden products cloned, pushed and mirrored through a second Git host; appended, wrapped and inserted calls of other names; a prepended same-name call; renames with `#[was]`, a second rename, and `--retire-was` | Untouched `CallSite`s and `EntityId`s unchanged; the prepend raises `ing/l-repeated-stage`, whose fix keeps later names; a second rename leaves one attribute holding the original name |
| ING-O-NAME-2 | One element inserted into or removed from geometry-driven patterns and query loops | Only that element's entities renamed |
| ING-O-CHECK-1 | Adding or removing any `require`; inserting a check before a named check; editing a check's limit | Every non-check node key unchanged; named checks keep their `CheckId`s, Evidence records and Waivers |
| ING-O-CHECK-2 | The gate predicate over generated outcomes, allowances and Waiver records | Matches contract section 5.6; `Warning` failures never block; `Undecided` blocks an `Error` check; `#[waive]` alone counts nowhere |
| ING-O-ASM-1 | Variant regions and Instance sets | Computed conditions rejected with `ing/2601`; a new hole changes a quantity, not the BOM structure |
| ING-O-TEXT-1 | Free-text spans on a labelled corpus; hidden characters; strings evaluated from untrusted spans | Classification matches; hidden characters fail with `ing/0003`; evaluated strings are `ExternalText` with their span's integrity, and node labels change only where text becomes a non-text value |
| ING-O-PERF-1 | Interpreter speed | Within the stated targets; Ingot's rebuild share reported |
| ING-O-PERF-2 | 500 concurrently suspended golden-product feature calls in a browser engine worker | Within the stated memory target |
| ING-O-PERF-3 | Data-module parsing on an ELX layout fixture of 10⁶ rows | Parsed and hashed in under 1 s natively (target); lossless round trip of edited rows |

## Phasing

| Phase | Ingot contribution to the gate |
| --- | --- |
| 0 | "Unit errors fail to compile" is ING-O-UNIT-1; the interpreter and Kiln protocol join the determinism suite (ING-O-EXEC-1, ING-O-EXEC-2); parser, types, interpreter and `CallSite`s (ING-O-NAME-1) in milestone 1 of contract section 13.2; the kind table generates `base`'s typed Rust views |
| 1 | GP1 and GP2 build from std Ingot on the interpreter: forwarded tolerances, zone contributions for GP1's bolt pattern, realized exports, `Approx`, the decision rule, named checks and the gate predicate, queries, sketches, GD&T, families, variant regions, packages, dialogs, the language service, tests; interpreter targets met (ING-O-PERF-1); the canonical bracket passes ING-O-BRK-1. The code generator and Perceus are deferred (contract section 13.2) |
| 2 | GP3 and GP4: Instance sets for fasteners, catalog selections, variants at scale; the data-module target measured (ING-O-PERF-3); the code generator if Ingot exceeds 2% (ING-O-EXEC-3); debugger and notebooks; reverse-mode derivatives; the first edition migration |
| 3 | GP5: ELX data modules and `network { … }` at scale; KCL importer (ING-O-TOOL-4) |
| 4 | GP6: large symbolic forms and parameter-domain forms in use (FLX) |
| 5 and later | Proposed: a mechanized soundness proof of the dimension and tolerance calculus, and a second interpreter for aerospace and medical certification |

Ingot's types for shared physics capabilities arrive early, but each capability takes its phase from contract section 13.4: Doyle–Fuller–Newman battery cells, for example, are phase 5.

## Open questions

None: every question this tab raised is decided, and none waits on an outside input.

## Contract change requests

None.

## Sources

| Key | Title | URL | Date opened |
| --- | --- | --- | --- |
| Zoo KCL reference | Zoo, "KCL Language Reference" | https://zoo.dev/docs/kcl-lang | 2026-10-11 |
| Zoo KCL units | Zoo, "Numeric types and units" | https://zoo.dev/docs/kcl-lang/numeric | 2026-10-11 |
| Zoo KCL pipelines | Zoo, "Pipelines" | https://zoo.dev/docs/kcl-lang/pipelines | 2026-10-11 |
| Zoo KCL functions | Zoo, "Functions" | https://zoo.dev/docs/kcl-lang/functions and https://raw.githubusercontent.com/KittyCAD/modeling-app/main/docs/kcl-lang/functions.md | 2026-10-11 |
| Zoo KCL modules | Zoo, "Projects and modules" | https://zoo.dev/docs/kcl-lang/modules | 2026-10-11 |
| Zoo KCL settings | Zoo, KCL settings | https://raw.githubusercontent.com/KittyCAD/modeling-app/main/docs/kcl-lang/settings.md | 2026-10-11 |
| KittyCAD modeling-app | KittyCAD, modeling-app repository, licence and kcl-lib README | https://github.com/KittyCAD/modeling-app and https://raw.githubusercontent.com/KittyCAD/modeling-app/main/LICENSE and https://github.com/KittyCAD/modeling-app/blob/main/rust/kcl-lib/README.md | 2026-10-11 |
| kcl-lib docs | kcl-lib API documentation | https://docs.rs/kcl-lib/latest/kcl_lib/ | 2026-10-11 |
| Onshape FeatureScript intro | Onshape, "Introduction to FeatureScript" | https://cad.onshape.com/FsDoc/intro.html | 2026-10-11 |
| Onshape FeatureScript UI | Onshape, FeatureScript UI specification | https://cad.onshape.com/FsDoc/uispec.html | 2026-10-11 |
| Onshape FeatureScript library | Onshape, FeatureScript standard library | https://cad.onshape.com/FsDoc/library.html | 2026-10-11 |
| Onshape FeatureScript variables | Onshape, FeatureScript variables and value semantics | https://cad.onshape.com/FsDoc/variables.html | 2026-10-11 |
| Onshape configurations | Onshape Help, "Configurations" | https://cad.onshape.com/help/Content/configurations.htm | 2026-10-12 |
| PTC Creo dimension bounds | PTC Creo Help, "To Set the Dimension Bounds" | https://support.ptc.com/help/creo/creo_plus/usascii/model-based_definition/to_set_the_dimension_bounds_1.html | 2026-10-12 |
| SolidCraft | SolidCraft repository and README | https://github.com/bherbruck/solvecraft | 2026-10-12 |
| CadQuery intro | CadQuery introduction | https://cadquery.readthedocs.io/en/latest/intro.html | 2026-10-11 |
| build123d builders | build123d, builder concepts | https://build123d.readthedocs.io/en/latest/key_concepts_builder.html | 2026-10-11 |
| build123d selection | build123d, topology selection | https://build123d.readthedocs.io/en/latest/topology_selection.html | 2026-10-11 |
| OpenSCAD manual | OpenSCAD User Manual, General, and repository | https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/General and https://github.com/openscad/openscad | 2026-10-11 |
| mp-units affine space | mp-units, the affine space | https://mpusz.github.io/mp-units/latest/users_guide/framework_basics/the_affine_space/ | 2026-10-11 |
| mp-units quantities | mp-units, systems of quantities | https://mpusz.github.io/mp-units/latest/users_guide/framework_basics/systems_of_quantities/ | 2026-10-11 |
| mp-units strong angular | mp-units, strong angular system | https://mpusz.github.io/mp-units/latest/users_guide/systems/strong_angular_system/ | 2026-10-11 |
| Pint offset units | Pint, non-multiplicative units | https://pint.readthedocs.io/en/stable/user/nonmult.html | 2026-10-11 |
| F# units of measure | Microsoft, F# units of measure | https://learn.microsoft.com/en-us/dotnet/fsharp/language-reference/units-of-measure | 2026-10-11 |
| JCGM publications | BIPM, JCGM publications (GUM, Supplements 1 and 2) | https://www.bipm.org/en/committees/jc/jcgm/publications | 2026-10-11 |
| Affine arithmetic | Wikipedia, "Affine arithmetic" (for Comba and Stolfi 1993; de Figueiredo and Stolfi 2004) | https://en.wikipedia.org/wiki/Affine_arithmetic | 2026-10-11 |
| ASME Y14.5 | ASME, Y14.5 Dimensioning and Tolerancing | https://www.asme.org/codes-standards/find-codes-standards/y14-5-dimensioning-tolerancing | 2026-10-11 |
| ASME Y14.5.1 | ASME, Y14.5.1-2019 | https://www.asme.org/codes-standards/find-codes-standards/y14-5-1m-mathematical-definition-dimensioning-tolerancing-principles/2019 and https://www.asme.org/codes-standards/find-codes-standards/y14-5-1-mathematical-definition-dimensioning-tolerancing-principles | 2026-10-11 |
| ISO 1101 | ISO 1101:2017 | https://www.iso.org/standard/66777.html | 2026-10-11 |
| ISO 5459 | ISO 5459:2024 | https://www.iso.org/standard/87855.html | 2026-10-11 |
| ISO 14405-1 | ISO 14405-1:2016 (withdrawn) and ISO 14405-1:2025 | https://www.iso.org/standard/65202.html and https://www.iso.org/standard/80703.html | 2026-10-11 |
| ISO 286-1 | ISO 286-1:2010 | https://www.iso.org/standard/45975.html | 2026-10-11 |
| ISO 22081 | ISO 22081:2021 | https://www.iso.org/standard/72514.html | 2026-10-11 |
| ISO 8015 | ISO 8015:2011 | https://www.iso.org/standard/55979.html | 2026-10-11 |
| Cranelift | Cranelift README | https://github.com/bytecodealliance/wasmtime/blob/main/cranelift/README.md | 2026-10-11 |
| Jangda 2019 | Jangda, Powers, Berger and Guha, "Not So Fast: Analyzing the Performance of WebAssembly vs. Native Code", USENIX ATC 2019 | https://www.usenix.org/conference/atc19/presentation/jangda | 2026-10-11 |
| Xu and Kjolstad | Xu and Kjolstad, "Copy-and-Patch Compilation" | https://arxiv.org/abs/2011.13127 | 2026-10-11 |
| Wasmtime determinism | Wasmtime, deterministic execution | https://docs.wasmtime.dev/examples-deterministic-wasm-execution.html | 2026-10-11 |
| Wasmtime tiers | Wasmtime, platform support and tiers | https://docs.wasmtime.dev/stability-platform-support.html and https://docs.wasmtime.dev/stability-tiers.html | 2026-10-11 |
| Wasm 3.0 profiles | WebAssembly 3.0 specification, profiles appendix | https://webassembly.github.io/spec/core/appendix/profiles.html | 2026-10-11 |
| WIT reference | Component Model, WIT reference | https://component-model.bytecodealliance.org/design/wit.html | 2026-10-11 |
| wit-bindgen | wit-bindgen | https://github.com/bytecodealliance/wit-bindgen | 2026-10-11 |
| jco | jco | https://github.com/bytecodealliance/jco | 2026-10-11 |
| wasm-instrument | wasm-instrument | https://github.com/paritytech/wasm-instrument | 2026-10-11 |
| wasmi | wasmi | https://github.com/wasmi-labs/wasmi | 2026-10-11 |
| Reinking 2021 | Reinking, Xie, de Moura and Leijen, "Perceus: Garbage Free Reference Counting with Reuse" (PLDI 2021, extended version) | https://www.microsoft.com/en-us/research/publication/perceus-garbage-free-reference-counting-with-reuse/ | 2026-10-11 |
| CORE-MATH | CORE-MATH project | https://core-math.gitlabpages.inria.fr/ | 2026-10-11 |
| Salmon 2011 | Salmon, Moraes, Dror and Shaw, "Parallel Random Numbers: As Easy as 1, 2, 3" (SC11) | https://www.thesalmons.org/john/random123/papers/random123sc11.pdf | 2026-10-11 |
| Reissmann RVSDG | Reissmann, Meyer, Bahmann and Själander, "RVSDG: An Intermediate Representation for Optimizing Compilers" | https://arxiv.org/abs/1912.05036 | 2026-10-11 |
| Omar typed holes | Omar, Voysey, Chugh and Hammer, "Live Functional Programming with Typed Holes" | https://arxiv.org/abs/1805.00155 | 2026-10-11 |
| Sketch-n-Sketch | Chugh, Hempel, Spradlin and Albers, "Programmatic and Direct Manipulation, Together at Last" | https://arxiv.org/abs/1507.02988 | 2026-10-11 |
| SketchGraphs | Seff, Ovadia, Zhou and Adams, "SketchGraphs" | https://arxiv.org/abs/2007.08506 | 2026-10-11 |
| rowan | rowan, and rust-analyzer's syntax documentation | https://github.com/rust-analyzer/rowan and https://github.com/rust-lang/rust-analyzer/blob/master/docs/book/src/contributing/syntax.md | 2026-10-11 |
| Salsa | Salsa overview | https://salsa-rs.github.io/salsa/overview.html | 2026-10-11 |
| PubGrub | PubGrub guide and pubgrub-rs | https://pubgrub-rs-guide.pages.dev/ and https://github.com/pubgrub-rs/pubgrub | 2026-10-11 |
| Rust editions | The Rust Edition Guide | https://doc.rust-lang.org/edition-guide/editions/index.html | 2026-10-11 |
| LSP 3.17 | Language Server Protocol 3.17 | https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/ | 2026-10-11 |
| DAP | Debug Adapter Protocol overview and specification | https://microsoft.github.io/debug-adapter-protocol/overview and https://microsoft.github.io/debug-adapter-protocol/specification | 2026-10-11 |
| SE-0289 | Swift Evolution SE-0289, result builders | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0289-result-builders.md | 2026-10-11 |
| MDN wasm-unsafe-eval | MDN, `script-src` and `'wasm-unsafe-eval'` | https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/script-src | 2026-10-11 |
| UAX 31 | Unicode Standard Annex #31, "Unicode Identifiers and Syntax" | https://www.unicode.org/reports/tr31/ | 2026-10-11 |
| Ryu | Ryū, shortest round-tripping floating-point output | https://github.com/ulfjack/ryu | 2026-10-11 |
| OCaml extensible variants | OCaml manual, extensible variant types | https://ocaml.org/manual/5.2/extensiblevariants.html | 2026-10-11 |
| Zoo KCL edge references | Zoo, "Edge references" | https://zoo.dev/docs/kcl-lang/edge-references | 2026-10-11 |
| OpenSCAD customizer | OpenSCAD User Manual, Customizer | https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Customizer | 2026-10-11 |
| OpenSCAD cheat sheet | OpenSCAD cheat sheet | https://openscad.org/cheatsheet/ | 2026-10-11 |
| SketchGraphs repository | SketchGraphs repository | https://github.com/PrincetonLIPS/SketchGraphs | 2026-10-11 |
| rr | rr, record and replay debugger | https://rr-project.org/ | 2026-10-11 |
| Sigmetrix CETOL | Sigmetrix, CETOL 6σ | https://www.sigmetrix.com/software/cetol | 2026-10-12 |
| CADforum ISO 286-2 | CADforum, shaft and hole tolerances by ISO 286-2 | https://www.cadforum.cz/en/tolerance.asp | 2026-10-11 |
| SIX ISO 4217 | SIX, ISO 4217 currency code list one | https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xml | 2026-10-11 |
