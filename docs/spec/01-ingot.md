# Ingot language (ING)

Ingot is Crucible's design language: pure, strict and statically typed, with units, tolerances, approximation error and geometric references as types. A canonical-class interpreter runs it on every target, and each operation call becomes a Kiln node named from source text alone. The visual editor, the code editor and agents edit one lossless syntax tree, so every edit is a minimal, mergeable source change.

## Scope and principles

| ING owns | Others own |
| --- | --- |
| Syntax, grammar, formatting, editions | Operation semantics and behavior versions (ANV, FLX) |
| Types: `Quantity<D>`, `Tol<T>`, `Approx<T>`, `Truth`, `Expr<T>`, `CheckId`, `CheckOutcome` | `ErrorBound`, `ErrorBudget`; `Field` (FLX) |
| `CallSite`; query syntax and lowering; the decision rule for `Truth`; the gate predicate | `EntityId`, lineage and `anvil::resolve` (ANV) |
| Evaluation semantics, `Failure` and `Abort` in the language, per-call limits | Scheduling, caching, labels, evaluation-wide limits, limit outcomes (KLN); determinism mechanisms (PLT) |
| The interpreter, the Ingot IR and the deferred code generator | The kernel IR (FLX, `kernels`); the determinizer (PLT) |
| Diagnostics, fixes and check semantics | Release policy, policy allowances and Waiver records (KLN); the verifier and `api` (AGT) |
| Modules, manifest language keys, lockfile `[language]`, semantic-version rules | Registry and signing (ECO); lockfile storage and merge (KLN) |
| `#[ingot::feature]`, the guest SDK and WIT bindings | WIT worlds and capabilities (ECO) |
| Feature metadata, language service, debugger, tests | Dialog rendering and code panel (UIX); agent tools (AGT) |

| Crate (contract section 12) | Contents | Phase |
| --- | --- | --- |
| `ingot-syntax` | Lexer, block-local parser, lossless tree, formatter, edition migrations | 0 |
| `ingot-types` | Name resolution, inference, dimension and tolerance algebra, diagnostics catalog | 0 |
| `ingot-ir` | Ingot IR (IIR), lowering, `CallSite`s, the reference interpreter, differentiation | 0 |
| `ingot-bindgen`, `ingot-macros` | WIT bindings, the generated guest SDK `ingot_sdk`, `#[ingot::feature]` | 1 |
| `ingot-service` | Language server, structural edits, test runner; debugger and notebooks | 1; 2 |
| `ingot-codegen` | IIR to WebAssembly, entering only when justified ("Execution") | 2 at the earliest |

Every Ingot crate is `forbid(unsafe_code)`.

1. **Pure.** No expression observes time, randomness, files, network, thread order, addresses or entity names; randomness is an explicit keyed value.
2. **Strict and bounded.** Call by value, left to right; every node ends in a value or a typed `Failure`.
3. **Physics in types.** Dimensions, affine quantities, tolerances and approximation error are types.
4. **Names from text.** Code never holds an entity index, and call-site identities come from source text only.
5. **One program, three editors.** Every GUI action and agent edit is a minimal edit of the lossless tree.
6. **No privileged code.** std is ordinary Ingot, reaching operations through `extern` declarations anyone can write.
7. **Errors are values with fixes.** A `Failure` has a code, a reason, a location and typed fixes; an `Abort` is not a value.
8. **No macros.** Builder blocks, attributes and generics cover what macros would.

**Decision D-ING-1:** Ingot is a pure, strict, expression-oriented language with immutable values, inference inside bodies, and required signatures on named items. *Why:* signatures let each module type-check alone, bound recompilation, and generate dialogs and documentation. *Rejected:* whole-program inference (distant errors); dynamic typing as in CadQuery (late unit errors); mutation (breaks dataflow lowering); laziness (demand-dependent costs).

### The language at a glance

The canonical example of contract section 6, unchanged:

```
use std::mech::{sketch, rect, extrude, rib, fillet, part}
use std::materials::alu_6061_t6
use std::sim::quick::static_stress

/// L-bracket with a stiffening web.
#[feature(category: "Structure", icon: "bracket")]
pub feature bracket(
    #[ui(step: 5mm)]
    width: Length in 20mm..=400mm = 60mm,
    thickness: Length = 4mm ± 0.1mm,
    load: Force = 1.2kN,
) -> Part {
    let outline = rect(width, 40mm)
    let base = sketch(plane.xy) { outline } |> extrude(thickness)
    let web = base.edge(role: end(outline.top)) |> rib(height: 20mm, t: thickness)
    let body = base + web
    let solid = body |> fillet(body.edges(new), 2mm)
    let p = part(solid, name: "Bracket").material(alu_6061_t6)
    let clamp = base.face(role: start_cap)
    let study = static_stress(p, fixed: clamp, force: load, on: web.face(role: end_cap))
    let stress = study.von_mises.max(over: p.away_from([clamp, web.face(role: end_cap)], 2 * thickness))
    p.require(stress < 0.6 * p.material.yield_strength(at: 20degC))
}
// width + load  →  error ING3001: cannot add Length and Force
```

`thickness` arrives as a `Tol<Length>`: the body computes with the nominal, and `extrude` records the tolerance as PMI (D-ING-4). The web's edge is chosen by its role, `end(outline.top)`, never by rank. `stress` is an `Approx<Stress>` away from the clamp and the loaded face (FLX), so the check is three-valued (D-ING-7).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Canonical example | Contract section 6 compiles, and its check decides at `SignOff` | Any other diagnostic or outcome fails the oracle | ING-O-31 | 1 |
| Purity | No expression observes time, randomness, files, network, thread order, addresses or names | Not expressible | ING-O-1 | 0 |

## Lexical syntax and grammar

### Source text

| Aspect | Rule |
| --- | --- |
| Encoding | UTF-8 in NFC, normalized by the platform layer on load; non-NFC input that bypassed it fails with `ING0002` |
| Hidden characters | Bidirectional controls, zero-width characters and Unicode tag characters are rejected anywhere in source (`ING0003`); string literals write them as escapes such as `\u{200B}` |
| Line endings | LF; CRLF is accepted and normalized by the formatter |
| Identifiers | UAX #31 default identifiers (an `XID_Start` character, then `XID_Continue` characters), with `_` added to the start set as the standard allows; `ING-L-MixedScript` flags mixed scripts |
| Case | `snake_case` for functions, features, variables, fields and modules; `PascalCase` for types, traits and enum variants; deny-by-default lint `ING-L-Naming` |
| Statements | A newline ends a statement unless inside brackets, after a binary operator, `,` or `\|>`, or before a line starting with `.`, `\|>`, `else`, `and`, `or` or `±`. No semicolons |
| Comments | `//` and nesting `/* … */`; `///` documents the next item and `//!` the module, both CommonMark |
| Attributes | `#[name(args)]` on the next item, parameter, field or statement; `#![name(args)]` on the module |
| Keywords | `and`, `as`, `else`, `enum`, `extern`, `false`, `feature`, `fn`, `for`, `if`, `impl`, `in`, `let`, `match`, `not`, `or`, `pub`, `record`, `require`, `self`, `Self`, `trait`, `true`, `try`, `type`, `use`, `where` |
| Contextual keywords | `kind` at item position, `table` before `{`, `package` and `super` in paths |

There is no `while` and no `return`. `%` is the percent suffix, so remainders are the functions `rem` and `mod`.

### Literals and units

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

A unit attaches to its number with no space, so `2in` is two inches and `2 in r` tests membership. The lexer takes the longest unit name, and letters that form no unit are an error (`ING0201`). A compound unit sits in brackets, and an exponent needs digits after `e`, so `1eV` is one electronvolt.

The unit table is closed per edition, and packages cannot add units; the knot is the constant `std::units::knot`. Prefixes compose only where defined, so `ft` is never a femtotonne.

| Unit set | Members |
| --- | --- |
| SI | SI units with SI prefixes; the radian |
| Accepted non-SI | `min`, `h`, `L`, `t`, `bar`, `eV`, `deg`, `rev`, `arcmin`, `degC`, `degF`, `degR` |
| US customary | `in`, `ft`, `thou`, `lb`, `lbf`, `psi` |
| Rotational | D-ING-3's named units |

Canonical spellings are ASCII (`um`, `deg`, `degC`, `ohm`). The formatter rewrites `µm`, `°`, `Ω` and `+-`, and `±` is the one non-ASCII token.

**Decision D-ING-2:** Every dimensional literal carries its unit, nothing declares a default unit, and literals convert to SI by exact rational arithmetic with one rounding. *Why:* KCL's documentation calls a bare number "possibly any of them", and exact conversion makes `25.4mm == 1in` hold bit for bit. *Rejected:* KCL's `defaultLengthUnit` (meaning depends on the file); a floating-point factor (double rounding); a unitless zero.

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

Named arguments may appear anywhere, and positional arguments fill the remaining parameters in order; `ING-L-NameArguments` asks for names after the second. Within one block each `let` name is unique (`ING1102`), so every statement has a stable textual name. There is no ad hoc overloading: one name has one signature.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Lexing and parsing | Every byte round-trips; malformed input becomes `ERROR` nodes inside its block | `ING0xxx` diagnostics; never a crash or hang | ING-O-2, ING-O-3, ING-O-29 | 0 |
| Hidden-character rejection | Bidirectional, zero-width and tag characters only as escapes | `ING0003` with an escape fix | ING-O-32 | 0 |
| Quantity literals | Exact rational conversion with one rounding; closed unit table per edition | `ING0201` unknown unit; `ING3001` dimension mismatch | ING-O-4 | 0 |
| Grammar | The EBNF above, with newline-terminated statements | `ING0xxx` with the expected tokens | ING-O-2, ING-O-5 | 0 |
| Unique statement names | One `let` name per block | `ING1102` with a rename fix | ING-O-5 | 0 |

## Types and dimensions

### Core types

| Type | Values and rules |
| --- | --- |
| `Bool` | `true`, `false` |
| `Int` | 64-bit signed; overflow fails with `ING6101`, never wraps |
| `Real` | Finite binary64, exactly `Quantity<1>`; producing NaN or an infinity fails with `ING6102` |
| `Quantity<D>` | A `Real` in coherent SI units with dimension `D`; checked at compile time, erased at run time |
| `Temperature` | An absolute temperature, affine ("Affine quantities") |
| `Complex<Q>` | Pairs of one dimension; the imaginary unit is `im` |
| `Decimal` | Exact decimals at 10⁻⁹ in a 128-bit integer, for `Money<C>` and counted data; products and quotients round half to even; inexact literals fail (`ING2003`) |
| `String`, `ExternalText` | Immutable NFC text; untrusted text with origin, written `external("…")`, never implicitly a `String` (AGT) |
| `Tol<T>`, `Approx<T>`, `Truth`, `Expr<T>` | Tolerances, approximations, three-valued results, staged symbolic values |
| `Body`, `Part`, `Assembly`, `Instance`, `InstanceSet`, `Field<D, V>`, `Material` | Handles to values Kiln holds |
| `Query<K>`, `Entity<K>` | Selections and resolved entities of kind `Face`, `Edge`, `Vertex`, `Region`, `Point` or `ShapeAspect` |
| `Point3`, `Vec3<D>`, `Direction`, `Transform`, `Plane`, `Axis`, `CoordSys` | Geometric values; `Point3` is affine over `Length` |
| `Seed`, `Rng` | Explicit randomness ("Evaluation") |

`width / 2mm` is a `Real`, so every dimensionless ratio is one type. `Int` multiplies quantities directly (`i * 6mm`); above 2⁵³ in magnitude that fails with `ING6103` rather than rounding.

ISO 4217's list gives at most four minor-unit digits (CLF, UYW), so 10⁻⁹ leaves five more for unit prices of small parts. Where a value becomes an amount payable (MFG), `round_minor(currency)` rounds it to the minor unit, and `ING-L-UnroundedAmount` flags a payable amount without it.

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

`kind X = D` names a dimension, and `kind X: D` declares an ISO 80000 quantity kind, which never adds to or compares with another kind of its dimension. Results are unkinded until they meet an annotation, and mixing kinds fails with `ING3002`, which offers an `as` cast.

The prelude declares kinds only where confusion causes real errors, such as frequency against angular frequency or activity (mp-units notes that hertz, becquerel and baud share `T⁻¹`). A new std kind needs an RFC (ECO) naming a seeded error it prevents, which joins ING-O-4's corpus.

| Expression | Rule |
| --- | --- |
| `a + b`, `a - b`, comparisons, `min`, `max` | Same dimension and compatible kind |
| `a * b`, `a / b` | Exponents add or subtract; `Int / Int` is a `Real`; `div`, `rem` and `mod` are integer operations |
| `a ^ n` | `n` is a compile-time rational unless `a` is dimensionless |
| `sqrt`, `cbrt` | Exponents halve or divide by three |
| `sin`, `cos`, `tan` | Take an `Angle` or a dimensionless phase; return `Real` |
| `asin`, `acos`, `atan`, `atan2(y, x)` | Return `Angle` |
| `exp`, `ln`, `log10` | Take and return `Real`; `ln(p / p0)` is the idiom |

Rotational kinds follow the strong angular system of contract section 5: `Torque` is J/rad, `MomentOfInertia` kg·m²/rad², `RotationalStiffness` J/rad² and `AngularVelocity` rad/s. `Nm` is newton metre per radian, and energy is `J` or `[N*m]`. Power τω, work τθ, τ = Iα and ½Iω² type-check without casts, as does each `Network` port's power expression.

An oscillation's angular frequency is an `AngularFrequency` (T⁻¹) and a phase is dimensionless, so ω = √(k/I), the reactance ωL in ohms and `cos(omega * t)` type-check. A rotation becomes a phase only through the constant `radian` or a std function such as `electrical_angle(theta, poles)`. The mp-units guide gives angular frequency in rad/s; Ingot keeps rad/s for rotation only.

A dimensionless phase would let `sin(f * t)` with `f` in hertz compile without the 2π. The deny-by-default lint `ING-L-HertzPhase` fires when a product with a `Frequency` factor reaches a trigonometric argument without passing through `AngularFrequency`. Its machine-applicable fix rewrites `f * t` as `f.angular() * t`, where `f.angular()` is 2πf.

**Decision D-ING-3:** Plane angle is a base dimension, never cancelled implicitly; rotational kinds follow the strong angular system, oscillation angular frequency is a kind of T⁻¹, and phase is dimensionless. *Why:* with torque in N·m each law of rotation carried a stray radian (R3-29), and ω in rad/s would put one into ωL. *Rejected:* a dimensionless angle (`3000rpm` becomes 314 Hz); torque in N·m beside a base angle; implicit cancellation. (revised in round 2)

### Inference and scalar flavors

Every named item states its signature; bodies are inferred bidirectionally. Dimension equations are linear over ℚ, so Gaussian elimination yields a most general solution. F# checks units with integer exponents; Ingot allows rational ones.

```
fn rms<D>(xs: [Quantity<D>]) -> Quantity<D> { sqrt(sum(xs.map(|x| x * x)) / xs.len()) }
```

| Rule | Premises | Conclusion |
| --- | --- | --- |
| Add, Sub | `a, b : Quantity<D>`, kinds compatible | `Quantity<D>`, with the shared kind |
| Mul, Div | `a : Quantity<D1>`, `b : Quantity<D2>` | `Quantity<D1·D2>`, `Quantity<D1/D2>`, unkinded |
| Pow | `n` a constant in ℚ | `Quantity<Dⁿ>` |
| Affine | `p, q : P`, `P: Affine`, `d : P::Delta` | `p - q : P::Delta`; `p ± d : P` |
| Compare | Exact operands; any `Approx` operand | `Bool`; `Truth` |
| Compare tolerances | Any `Tol` operand | `ING4101`, with fixes that state the meaning |
| Mix | A `Tol` and an `Approx` operand | `ING4102`: convert the tolerance with `.limits()` first |

Let bindings are not generalized. Integer literals adopt `Int`, `Real` or `Decimal` from the expected type, with no other implicit conversion.

A quantity has four flavors, all implementing the trait `Scalar<D>`: exact `Quantity<D>`, `Tol`, `Approx` and `Expr`. Arithmetic and std math are generic over `Scalar`, and a parameter written `Length` accepts any `Scalar<L>` in `fn` and `feature` alike. Each call is monomorphized per flavor.

| Flavor | In the body | Result |
| --- | --- | --- |
| `Quantity<D>` | The value | Exact |
| `Tol<Quantity<D>>` | The nominal; passing it on forwards the tolerance (D-ING-4) | Exact, unless returned itself |
| `Approx<Quantity<D>>` | The value and its budget, propagated by arithmetic | `Approx`; only `Guaranteed` bounds cross a feature boundary |
| `Expr<Quantity<D>>` | A symbolic value; the body is staged (D-ING-9) | `Expr` |

A parameter that must be exact is written `Exact<Length>`. Three coercions remain: `T` to `Option<T>`, an unkinded quantity to a kind, and a value to an `#[implicit]` enum variant (`extrude(10mm)` means `extrude(Blind(10mm))`).

**Decision D-ING-20:** Quantities have four flavors under one trait, `Scalar<D>`: a quantity parameter accepts every flavor at every call position with one meaning per flavor, and `Exact<D>` opts out. *Why:* round 1's per-position lifting rejected `rect(other.edge(…).length(), 10mm)` and symbolic values in plain functions (R3-31). *Rejected:* coercions at feature positions only; generic signatures on every helper (ceremony).

### Affine quantities

Absolute temperature is a point, as in mp-units' affine space and Pint's offset units: point minus point is a difference, and points never add or multiply.

| Literal or expression | Type |
| --- | --- |
| `20degC`, `68degF`, `absolute_zero + 77K` | `Temperature` |
| `15K`, `27degR`, `5delta_degC`, `t1 - t2` | `TemperatureDifference` |
| `t.absolute()` | `TemperatureDifference` above absolute zero, for radiation and gas laws |
| `200[W/(m*degC)]`, `150[ppm/degC]` | Inside compound units `degC` and `degF` mean differences, as datasheets write them |
| `t1 + t2`, `2 * t` | `ING3201`, with fixes `.absolute()` or a difference |

`Tol<P>` and `Approx<P>` for an affine `P` carry deviations and bounds in `P::Delta`. `Point3` follows the same rules.

Quantities are stored in coherent SI units as binary64, and source keeps literals as written. Display units (UIX) map kinds to units per package, user or view without changing values. Values print as the shortest round-tripping decimal (Ryū), and generated literals keep the unit at their position.

### Records, enums, traits and collections

```
pub record DowelSpec { diameter: Length, length: Length, chamfer: Option<Length> = none }
pub enum Extent<Q = Length> { #[implicit] Blind(Q), Symmetric(Q), UpTo(Query<Face>), ThroughAll }

let longer = DowelSpec { ..spec, length: 30mm }        // functional update
let kind = match extent { Blind(d) if d > 50mm => "deep", Blind(_) | Symmetric(_) => "blind", _ => "through" }
```

Records are nominal when declared and structural when written `{ a: Length }`. A structural type may spread another, `{ item: ItemNumber, ..Params<bracket> }`, when shared fields agree (`ING2105`). `Expr<T, Out>` carries declared derived outputs, so `result.von_mises` is a typed field (FLX).

Enums are tagged unions with exhaustive `match`, and `#[non_exhaustive]` enums need a wildcard arm outside their package. Type parameters are monomorphized and dimension parameters erased; a bound `D: Dim` passes a dimension when an accessor must check one. Coherence follows Rust's orphan rule, and `dyn Trait` boxes heterogeneous values.

A `Field<D, V>` takes a product domain written as a tuple, `Field<(Body, Time), Temperature>`, and quantity kinds name parameter domains. `kind ParticleRadius: L` thus types a DFN particle concentration as `Field<(Body, ParticleRadius), Concentration>` (D-FLX-38).

| std trait | Implemented by |
| --- | --- |
| `Eq`, `Ord`, `Hash` | Numbers, strings, records and enums by derivation; `Query` by its canonical plan; `Entity<K>` by canonical geometric order |
| `Affine` | `Temperature`, `Point3`, with an associated `Delta` |
| `Scalar<D>` | The four quantity flavors |
| `Transformable` | Bodies, Parts, points, planes, coordinate systems, queries |
| `Measure` | Distances, angles, areas, volumes, mass properties; returns `Approx<Q>` |
| `Feature` | Every `feature`: `Params`, `Output` and `metadata()`, so `family` and agent tool schemas work generically |
| `Check`, `Error` | `Bool`, `Truth` and std check records; typed failures with codes and fixes |

`Option<T>` has `some(x)` and `none`; `Result<T, E>` has `ok(x)` and `err(e)`, the one exception to the naming rule. `?` turns `err(e)` into a failure and `none` into `ING6201`.

| Type | Literal | Semantics |
| --- | --- | --- |
| `[T]` | `[1mm, 2mm]` | Persistent list |
| `Map<K, V>`, `Set<T>` | `["M6" => 6.6mm]`, `set([…])` | Ordered by `K`'s canonical order, so iteration is deterministic |
| `Range<T>` | `0..8`, `20mm..=400mm`, `..=5mm` | Also the interval type; `x in r` is a `Truth` for an `Approx` `x` |
| `Table<R>` | `table { … }`, `table("rows.csv")` | Rows of a record type, units checked against headers |

`Vec3<Length>`, `Mat3<Stress>` and `Mat<R, C>`, with a dimension per row and column as a Jacobian needs, are std types over the same algebra. A dimension error in a `Mat<R, C>` names the entry `(i, j)` with expected and actual dimensions. An `ING3001` note prints the row and column dimension vectors once.

A `Range` of quantities iterates only with an explicit step, `(0mm..=10mm).step(2mm)`.

`sum` is PLT's `det_sum` (contract section 7.3), so a list sums to the same bits in Ingot and inside an operation. `min` and `max` are exact in any order, and `fsum` returns the correctly rounded sum by exact accumulation.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Dimensions and kinds | Rational exponents over eight bases; kinds added by RFC; erased at run time | `ING3001`, `ING3002` with fixes | ING-O-4 | 0 |
| Strong angular system | Contract section 5 kinds; rotation and phase apart | `ING3001` with a `radian` fix; `ING-L-HertzPhase` | ING-O-4 | 0 |
| Inference, records, enums, traits | Bidirectional; exhaustive `match`; orphan rule | `ING2xxx` | ING-O-5 | 0 (core), 1 (traits, `dyn`) |
| Scalar flavors | One trait, every call position, `Exact<D>` opt-out | `ING2001`; `ING6403` at boundaries | ING-O-5, ING-O-8 | 1 |
| Affine quantities | Points and differences; compound units as differences | `ING3201` | ING-O-4 | 0 |
| Reductions | `sum` is `det_sum`; `fsum` correctly rounded | Not expressible | ING-O-1 | 0 |
| `Decimal` and `Money<C>` | Exact at 10⁻⁹; round half to even; currencies never mix | `ING6101`, `ING2003`; `ING-L-UnroundedAmount` | ING-O-5 | 1 |
| Product and parameter domains | `Field<(D, …), V>`; kinds name parameter domains | `ING2001` | ING-O-5 | 1 |

## Tolerances, approximations and truth

### `Tol<T>`

`Tol<T>` is opaque. It holds a `nominal`, a `center`, `terms` (one deviation coefficient per noise symbol), a `remainder` and its written `form`; `lower()`, `upper()` and `limits()` are methods. `T` is a quantity, `Real` or `Temperature`, whose deviations are `T::Delta`.

| Form | Ingot | Limits |
| --- | --- | --- |
| Symmetric | `4mm ± 0.1mm` | 3.9 mm to 4.1 mm |
| Deviations | `10mm ±(-0.1mm, +0.2mm)` | 9.9 mm to 10.2 mm; signs mandatory |
| Limits | `tol(9.9mm..=10.2mm)` | Nominal at the mid-limit |
| Fit code | `fit(10mm, H7)` | Computed from ISO 286-1's formulas, never a transcribed table (MEC) |
| Basic | `basic(30mm)` | Theoretically exact, toleranced by a GD&T control |

Inverted limits fail with `ING4001`, and a deviation of the wrong dimension with `ING4002`. A dimensionless deviation is relative only as a `%` or `ppm` literal.

An untoleranced length is exact in Ingot arithmetic. MEC's Part-level `general_tolerance(standard, class)` record supplies limits for untoleranced sizes in stacks, inspection and cost, so the language needs no implicit tolerance.

**Decision D-ING-4:** A `Tol<T>` may fill any slot declared as `T`; the slot holds the nominal, and the realizing feature records the forwarded site as PMI on an anchored aspect query. *Why:* geometry stays nominal, and a split target fails a check instead of losing its tolerance behind a Note (R8-12). *Rejected:* a tolerance on every `Length` (cost on temporaries); `.nominal` at every use (PMI loses it); attributes copied through operations, the round 2 rule. (revised in round 3)

### Arithmetic on tolerances

Each tolerance site (a `±` expression, `tol(…)` or `fit(…)`) owns a noise symbol εᵢ in [−1, 1]. A computed `Tol` is a center plus one coefficient per symbol. In this affine arithmetic (Comba and Stolfi 1993; de Figueiredo and Stolfi 2004), forms sharing a symbol are correlated, which removes interval arithmetic's dependency problem.

| Operation | Result |
| --- | --- |
| `a ± b`, `k * a`, `a / k` with exact `k` | Exact affine combination; `a - a` has zero width |
| `a * b`, `sqrt(a)`, other smooth functions | First-order term per symbol, plus a remainder bounding the rest over the joint box |
| `a < b` and other comparisons | `ING4101`; fixes offer `a.upper() < b.lower()`, `a.nominal < b.nominal` and `yield_of(…)` |

Rounding enters the remainder, so `.limits()` is a guaranteed enclosure in binary64. Forms store coefficients sparsely. A form above 4,096 symbols keeps the 4,096 largest coefficients and folds the rest into the remainder, losing only their correlation, and reports `Note::SymbolsCondensed { count, width }`.

Statistics are explicit calls that print their assumed distributions. `.rss(coverage: 99.73%)` returns the quantile interval of the first-order form (JCGM 100:2008), by exact convolution up to eight uniform or normal terms and numerically beyond. It intersects with `.limits()`, so it is never wider than the worst case; `k:` is accepted only when every contributor is normal.

`.monte_carlo(n:, rng:)` follows JCGM 101:2008. Sites declare distributions with `.statistical(Normal(cp: 1.33))` or an MFG process capability, else MEC's `default_distribution` applies (D-MEC-28). `group:` correlates parts from one reel or fixture.

A symbol stands for one manufactured characteristic:

1. A code-level site has one symbol, so a code-level stack keeps its correlations; a site inside a loop gets one symbol per key.
2. A tolerance forwarded into a Part is keyed by (site, realizing Part or Instance path), so two parts made from one specification vary independently.
3. A tolerance read from geometry (`aspect.size_tol()`, PMI) is keyed by the aspect's `EntityId` and Instance path.
4. `t.independent(key)` makes an independent copy, and `ING-L-SharedSymbol` flags one symbol entering an expression with both signs.

These keys use names only to decide which symbols are one symbol. Every numeric use orders symbols by a name-free key (contract section 7.1):

1. the absolute first-order sensitivity of the measured quantity, largest first, so Sobol's leading dimensions go to the largest contributors;
2. for a realized symbol, its Part's `GeometryId`, the placement and the aspect's canonical entity number; for a code-level one, the canonical hash of its position in the expression DAG;
3. the nominal, limits and distribution.

`.rss` sums in this order through `det_sum`, Sobol dimensions follow it, and each `.monte_carlo` stream is seeded from the key and argument values. Symbols equal under the whole key are exchangeable, so any assignment gives identical bits.

**Decision D-ING-5:** `Tol` arithmetic uses affine forms over per-site noise symbols, worst case by default; names decide which symbols are shared, and a name-free key orders every numeric use. *Why:* linear stacks must be exact, two spacers from one specification vary apart (R3-30), and statistics must survive renaming (R8-08, R9-17). *Rejected:* interval arithmetic (overestimates repeats); implicit RSS (hides a process assumption); name order (a rename moves Sobol dimensions). (revised in round 3)

MEC's variation analysis has two paths (D-MEC-22), both reading `tolerances(x)`, the sites behind `x`. The zone path samples small-displacement torsors per toleranced aspect and re-solves only the mate system. The rebuild path, for size tolerances that change topology or contact, calls `vary(f, sites)`, which samples sites through literal overrides as ordinary evaluations.

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

`clearance.limits()` is exactly 5 µm to 29 µm, as ISO 286-2's tables give over 6 mm up to 10 mm. With Cp = 1.0, σ is 2.5 µm for the bore and 1.5 µm for the pin. The upper limit is then 17 µm + 3 × 2.92 µm = 25.75 µm. Under MEC's uniform default the call convolves two uniforms and gives 28.4 µm, still inside the worst case.

### GD&T controls as types

MEC owns the GD&T records and validators; Ingot owns attachment and the mistakes the type checker catches.

1. **Typed aspects.** `Query<Aspect<K>>` selects shape aspects whose kind is static when the producing feature declares it: `hole(…)` gives `Aspect<OfSize>`, extrude caps `Aspect<Planar>`, recognized imports `Aspect<Any>`.
2. **Controls are values.** `position(…)`, `flatness(…)` and the others return `GeometricTolerance` records whose signatures carry the standards' rules as trait bounds. A material condition modifier needs `K: OfSize`.
3. **Typed attachment.** `part.tolerance(target, control)` records the control on an anchored aspect query, re-resolved on the final Part. Every PMI item, forwarded or explicit, has MEC's `Error`-severity check `pmi_target_resolved`. A split, merged or deleted target fails it, never degrading to a Note, and its fix inserts an explicit `part.tolerance(…)`.
4. **Dialects are modules.** `std::mech::gdt::asme` implements ASME Y14.5-2018. `std::mech::gdt::iso` implements ISO 1101:2017, ISO 5459:2024, ISO 14405-1:2025, ISO 8015:2011, ISO 22081:2021, ISO 5458 and ISO 2692, whose editions MEC states. The manifest key `gdt-dialect` names the design's dialect, and importing the other fails with `ING4302`.
5. **Tombstones.** Symbols ASME Y14.5-2018 deleted (concentricity, symmetry) are declared `#[removed(in:, instead:)]`, so a call fails with that explanation and fixes.

```
let a = datum("A", plate.face(role: start_cap))
let holes = plate.aspects(created_by: mount_holes)          // Query<Aspect<OfSize>>
plate.tolerance(holes, position(dia(0.1mm), mmc, datums: [a, b, c.at(mmb)]))
// position(dia(0.1mm), mmc, …) on plate.face(role: start_cap)
//   → error ING4201: maximum material condition needs a feature of size; start_cap is Aspect<Planar>
```

Rules that need resolved geometry, such as datum degrees of freedom, run at build time and fail with MEC's `InvalidControl { rule, clause }`. ASME's page for Y14.5.1-2019 calls it consistent with Y14.5M-1994, so MEC defines the zone mathematics of each Y14.5-2018-only construct and marks it `CrucibleDefined` in reports.

**Decision D-ING-6:** GD&T controls are ordinary records from dialect modules; legality rules are trait bounds on typed aspects where the kind is static, and the rest run at build time. *Why:* the commonest GD&T errors (modifiers on surfaces, deleted symbols, mixed dialects) become compile errors at their line. *Rejected:* a GD&T sublanguage (a second grammar); build-time validation only (late); string-encoded control frames (untyped).

### `Approx<T>` and the decision rule

`Approx<T>` is a value with an `ErrorBudget<T::Delta>` (contract section 5) in `Pointwise` and `Goal` norms, plus flags such as `Singular`. Measurements, Field reductions (`stress.max(over: R)`) and Wasm component results with declared errors return it. A reduction is `Quantified` only when Flux estimated that functional.

A material property read such as `p.material.yield_strength(at: 20degC)` also returns an `Approx`. Its input part is a `Guaranteed` enclosure from the lower to the upper basis value: the specification limit, else B-basis (COV). A comparison therefore decides conservatively whichever check consumes it, and the report names the basis and the deciding side.

Arithmetic propagates each source separately with outward rounding, keeping the product term (|xy − x̃ỹ| ≤ |x̃|·e_y + |ỹ|·e_x + e_x·e_y). A part's kind is the weakest of its inputs, and dividing by an enclosure containing zero fails with `ING6104`.

One rule decides every comparison of approximate values, in `if`, `match` guards, query `where:` and `require` alike. For `x < y` under `decides_on`, a bound kind (`Estimated` unless a check declares `Guaranteed`):

| Outcome | Condition |
| --- | --- |
| `True` or `False` | Every part is quantified and meets `decides_on`, the enclosures are disjoint, and no blocking flag is set |
| `Undecided { WithinBound, needed }` | The enclosures overlap; `needed` is the bound that would decide |
| `Undecided { Indicator }` | A part is only an `Indicator`: every `Preview` result, and any result outside its calibration envelope (FLX) |
| `Undecided { Unquantified(sources) }` | A part is `NotQuantified` (for `require`, see "Checks" for the conditional `Pass`) |
| `Undecided { CalibrationUnconfirmed }` | A `SignOff` decision rests on an `Estimated` discretization part, and the confirming refinement (contract section 7.1) disagrees |
| `Undecided { SingularPoint }`, `Undecided { Flagged(flag) }` | A blocking flag from the producer |

`==` on an `Approx` is `False` on disjoint enclosures and `Undecided` otherwise. `and`, `or` and `not` follow Kleene's strong three-valued logic, so `False and Undecided` is `False`.

A decided comparison carries its confidence, 1 − Σα over the parts that carry one, calibrated `Estimated` bounds included (contract section 5).

Each node records the fidelity of the bounds it observed. An `if`, `match` or `where:` on `Undecided` yields the value `Undecided { needed, fidelity }` at the node's effective fidelity. It is cached like any value, `try` cannot catch it, and dependents receive `DependencyUndecided`.

The Evaluation's fidelity ceiling changes only reporting. While a higher-fidelity node of the same target is demanded, the consumer shows `ResultStatus::Pending`. At the ceiling, the Evaluation report raises `ING6401 UndecidedBranch` with the margin and the accuracy needed.

**Decision D-ING-7:** Disjoint enclosures decide approximate comparisons under `decides_on`; control flow on `Undecided` yields a cached `Undecided` value, and the ceiling changes only reporting. *Why:* four tabs had four rules (R3-07), and a ceiling-dependent failure was cached and served to `SignOff` Evaluations (R9-02). *Rejected:* comparing estimates only; deciding on `Indicator` parts; `Undecided` as `False`; `Pending` and `ING6401` as node values, the round 2 rule. (revised in round 3)

`x.estimate()` discards a bound explicitly, and the language service marks it.

### Approximate values as inputs

Geometry is often driven by measured geometry, as in `rect(other.edge(role: end(r.top)).length(), 10mm)`. At a feature or operation boundary, an `Approx` argument passes only with a `Guaranteed` total. The call uses the value and records the bound in an `InputSensitivity` record for variation analysis.

Weaker bounds fail with `ING6403 EstimateAsInput`, whose fixes declare the parameter `Approx<T>` or write `.estimate()`. Representation error stays in Anvil's per-face bounds, so `body.convert(into: Mesh, tolerance: 0.01mm)` returns a `Body`.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `Tol<T>` forms and forwarding | Opaque affine form; nominal in slots; forwarded PMI on anchored aspect queries | `ING4001`, `ING4002`; `pmi_target_resolved` | ING-O-7, MEC-O-TL-1 | 1 |
| Affine tolerance arithmetic | Exact linear stacks; guaranteed enclosures; Part-keyed symbols; condensation | `ING4101`, `ING4102`; `ING-L-SharedSymbol` | ING-O-7 | 1 |
| Statistical combination | Explicit `rss(coverage:)` and `monte_carlo`; name-free symbol order | Assumptions printed | ING-O-7, ANV-O-LABEL-1 | 1 |
| GD&T attachment and dialects | Typed aspects, dialect modules, tombstones | `ING42xx`, `ING4302`, `InvalidControl` | MEC-O-TL-1, ING-O-5 | 1 |
| `Approx<T>` | Budgets in `Pointwise` and `Goal` norms; outward rounding; basis enclosures | `ING6104` | ING-O-8 | 1 |
| Decision rule | Disjoint enclosures decide under `decides_on`; Kleene logic; confidence | `Undecided { reason, needed }` | ING-O-8 | 1 |
| Undecided control flow | Cached `Undecided` value; ceiling changes reporting only | `DependencyUndecided`; `ING6401` in the report | ING-O-35 | 1 |
| Approximate inputs | `Guaranteed` only; bound into `InputSensitivity` | `ING6403` with two fixes | ING-O-8 | 1 |

## Geometry in the language

### Kiln-held values

`Body`, `Part`, `Assembly`, `Instance`, `InstanceSet`, `Field` and `Material` values are immutable handles to values Kiln holds and the CAS stores. Code calls operations and std features that return new handles. Handle equality is content equality (`ObjectId`), and `a.same_geometry(b)` compares name-free identities (`GeometryId`; MEC owns the Part and Assembly encodings).

| Type | Created by | Key members (std) |
| --- | --- | --- |
| `Body` | Operations and features; `+`, `-`, `&` | `faces`, `edges`, `regions`, `aspects`, `volume`, `bbox`, `mass_properties`, `convert(into:)` |
| `Part` | `part(body, name:, item:)` | `.body`, `.material(m)`, `.tolerance(target, control)`, `.require(…)`, `.csys(name)`; an unassigned material's property fails with `ING6701` |
| `Assembly` | `assembly(instances, mates:)` | `.instances()`, `.find(path)`, `.bom()`, `.interference()` |
| `Instance` | `instance(part_or_assembly, at:, fixed:)` | `.part`, `.placement`, `.csys(name)`, `.path` |
| `InstanceSet` | `instances(of:, at:, min:)` ("Assemblies, variants and families") | `.members()` keyed by anchor, `.member(key)`, `.count()` |
| `Field<D, V>` | Flux operations and std physics | Defined by FLX |

A chain such as `a + b + c` lowers to one n-ary `anvil::boolean` by a fixed rule, so one source gives one operation graph. The prelude defines `origin`, the directions `x`, `y` and `z`, the axes and the planes `plane.xy`, `plane.yz` and `plane.xz`. Reference geometry (`plane.offset`, `axis.of`, `point.on`) is MEC's `std::mech::refgeom`, anchored by queries.

### Call sites and names

An `Entity<K>` is a Body's `ObjectId` plus an `EntityId`, valid only with its Body; its accessors return `Approx` values. Anvil names entities by `CallSite` (D-ANV-14), which Ingot derives from source text alone (contract section 5). A `CallSite` is the path of call frames from the Evaluation's root; each frame, a feature or `fn` call, has three parts.

| Part | Rule | Stable under |
| --- | --- | --- |
| Statement | A `let` is (item path, arm path, binding name); an unnamed statement is (item path, arm path, preceding binding name, ordinal after it). Arm paths name `then`, `else` or a `match` pattern's canonical text | Edits elsewhere, moves, reformatting, literal edits, retyping |
| Call | The callee's name and its occurrence index among same-name calls in the statement | Calls of other names; a same-name call renames only later ones |
| Keys | One key per enclosing iteration ("Patterns, loops and keys") | Inserting or removing other elements |

Renaming a binding is a refactor that writes `#[was(old_name)]`, keeping the identity until a person removes the attribute. Live-collaboration block ids map onto these identities and never enter them (KLN). A Git round trip or a publication leaves every `EntityId` unchanged.

A same-name call inserted before others in one statement renames the later ones. The deny-by-default lint `ING-L-RepeatedStage` flags a statement with several entity-naming calls of one name, and its fix splits the statement into bindings.

**Decision D-ING-21:** `CallSite`s derive from source text: frames of statement identities from binding names, call identities from callee name and occurrence, and iteration keys. *Why:* block ids changed after a Git round trip or a retyped statement (R3-06, R2-02), and slot paths renamed every stage when one was appended (R2-06). *Rejected:* live-document block ids, the round 1 rule; slot paths; source offsets; a CRDT identity per call (not derivable from text).

Nothing in Ingot orders, numerically hashes or prints names. `Entity<K>` orders by Anvil's canonical geometric order, and `Seed::from(x)` hashes `x` with names removed, as label invariance requires (contract section 7.1).

A transform (`move`, `rotate`, `mirror`, `transform`) always keeps names, whatever else reads its source. When one operation receives two operands carrying one `EntityId`, as a Boolean or a combine can, Anvil relabels the operand from the later transform in program order. Its entities take role `copy` or `mirror`, keyed by that transform's `CallSite`, and `copy(x)` relabels at once.

`seed.face(role: top).copies()` follows copies on request, and role queries on reflections accept `mirrored: true` (D-ANV-30).

### The query language

A `Query<K>` describes a selection on a subject Body and re-resolves wherever it is used. Methods on a Body, Part, Instance or query build it; `Query<Point>` covers derived points such as `face.corners(inset:)`.

| Element | Syntax | Meaning |
| --- | --- | --- |
| Subject and count | `b.face(…)`, `b.faces(…)`, also `edge`, `vertex`, `region`, `aspect` | Singular needs one match; plural at least one unless `count:` says otherwise |
| Anchor | `part.face(base.face(role: end_cap))` | Descendants of the anchor through Anvil's lineage |
| Role | `role: end_cap`, `role: end(outline.top)`, `role: lateral(any)` | Entities created with that role, declared per entity kind with `#[roles(face: …, edge: …, vertex: …)]` (ANV owns std's vocabulary); a wrong-kind role fails with `ING5002` |
| Creator, history | `created_by: holes`; `new`, `modified`, `all` | Entities from the call site that produced `holes`; created or modified by the subject's operation |
| Geometric filters | `normal: +z`, `kind: Cylinder`, `area: 100mm2..`, `radius: 2.95mm..=3.05mm`, `parallel_to:`, `within:` | Certified predicates; a `Tol` argument fails with `ING4103`, so a selection never becomes a manufacturing tolerance |
| Topology | `.edges()` of a face query, `adjacent_to:`, `bounded_by:` | Adjacency in the subject |
| Rank selectors | `longest`, `largest`, `nearest: p`, `first(along: d)`, `last(along: d)` | Only after an anchor or role, else `ING-L-FragileSelector`; a near-tie winner carries `Note::NearTie { runner_up, margin }`, and ANV's sampled analysis reports `RankSwap` across ranges |
| Set algebra | `q1 + q2`, `q1 - q2`, `q1 & q2` | On one subject |
| Custom filter | `where: \|f\| f.area() > 2 * hole_area` | A predicate under the decision rule: `Undecided` shows `Pending` below the ceiling and `ResolveError::Ambiguous { entities, needed }` at it |
| Extent use | `on_merge: Accept`, `on_partial: Accept`, `on_fragile: Accept` | For an extent use, a merge, partial deletion, `Ordinal` id or near tie fails with a `ResolveError` unless accepted (contract section 5) |

```
let bores  = body.faces(kind: Cylinder, radius: 2.95mm..=3.05mm, created_by: holes)
let rim    = top.edges() - top.edges(adjacent_to: bores)
let lip    = body.edge(created_by: base, role: lateral(any), last(along: +x))   // rank after a role
let blends = body.faces(new)
```

A query resolves on the Body of the operation that consumes it, mapping its selection through lineage, so `fillet(solid, base.face(role: end_cap).edges())` works. A `Query` parameter resolves on the first `Body` or `Part` parameter unless `#[on(param)]` names another. Each query lowers to a canonical `QueryPlan` that `anvil::resolve` evaluates as its own node, and a `ResolveError` arrives at the query's span with ranked fixes.

There is no positional access (`ING5001`). `.resolve()` returns entities in canonical geometric order, `sorted_by` in a stated order, and `e.query()` anchors a query on one entity's `EntityId`. Resolution never silently picks another entity at the evaluated configuration (contract section 5).

**Decision D-ING-8:** Queries are values resolved by a separate `anvil::resolve` node: certified declarative filters, rank selectors only after an anchor or role, and arbitrary predicates as `where:` closures under the decision rule. *Why:* declarative filters can be certified, cached and explained, and one rule for every `Undecided` keeps queries consistent with branches (R9-20). *Rejected:* string selectors such as CadQuery's `">Z"`; positional slicing; unanchored ranks; a `where:` that fails at once, the round 2 rule. (revised in round 3)

### Builder blocks and sketches

A call may end with a block, as in `sketch(plane.xy) { outline }`, Swift's result-builder mechanism with a smaller rule. A function opts in with a final `Builder<I, Ctx>` parameter, and each statement whose type implements `Emit<I>` contributes its items (`ING2301` otherwise). A `let` names its items as result fields, so `let r = rect(…)` yields a `Sketch<{ r: Rect }>`.

`if`, `match` and `for` contribute their branches' or iterations' items, and a clash with an enclosing binding is `ING1104`. ELX's `network { … }` uses the same mechanism with set-like accumulation.

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

`chord_ratio`, an ordinary function over `Length`, accepts `Expr<Length>` (D-ING-20). Branching on a symbolic value fails with `ING2402`, and `select(cond, x, y)` builds conditional residuals. Local Newton solves use `local_solve(residual, x0)`, differentiated by the implicit function theorem (contract section 6).

**Decision D-ING-9:** Constraints, analytic Field expressions and weak forms are one mechanism: staged symbolic values built by ordinary functions and handed over as a hash-consed expression DAG. *Why:* one mechanism serves MEC's constraints, FLX's constitutive functions and analytic Fields, and equal expressions become equal keys. *Rejected:* a `constraint` keyword with its own subset; tracing code into the kernel IR (captures one branch). (revised in round 2)

`anvil::solve_constraints` solves a sketch block as one node. A solved point is an `Approx<Point3>`, `Guaranteed` when Anvil's Krawczyk test proves its block and `Estimated` otherwise; under-determined blocks are proved through their minimum-displacement KKT system (ANV, MEC).

SketchGraphs offers "15 million sketches extracted from real-world CAD models", and ING-O-23 converts a fixed sample into sketch blocks.

Seeds are literals, and a build never warm-starts from an earlier solve (MEC). A released sketch drag rounds seeds to a quantum q, by default the larger of 1 µm and 2¹⁰ times the sketch's resolution ρ, in decimal millimetres. It writes only entities that moved by more than q.

Before writing, the edit re-solves from the rounded seeds and checks that branch qualifiers and solution agree within the certified bound; otherwise it writes more digits.

**Decision D-ING-26:** Sketch seeds are inline literals rounded to a quantum, merged like any literal; concurrent edits to the seeds of one under-determined block conflict. *Why:* seeds decide under-determined sketches, so they are intent that travels with the text through review and Git export (R8-24). *Rejected:* a layout section merged by last writer (values outside the text; lost drags); full-precision seeds (textual conflicts).

### Assemblies, variants and families

An Instance's path lists instance names from the root (`drive/wheel`). A query through an Instance carries its placement, and mates take `CoordSys` values (MEC). A record marked `#[interface]` derives a `compatible(a, b)` check.

Variants are enum or record parameters marked `#[configuration]` on assembly features (contract section 6). Conditional regions that depend only on configuration parameters and constants are variant regions, whose Instances carry the region's condition. An Instance or Instance set under any other condition fails with `ING2601`, so Kiln computes the 150% BOM by abstract interpretation (KLN).

An Instance set separates existence from multiplicity. `instances(of: f, at: anchors)` places one member per anchor of a keyed list, typically a resolved query, as one BOM line whose existence follows the static rule. Members, count and per-member parameters are evaluated and keyed by anchor, so a new hole changes a quantity, not the BOM's structure.

```
let screws = instances(at: cover.aspects(created_by: bolt_holes), of: |h| iso4762(m6, length: grip(h)))
```

A set is empty only if it declares `min: 0`; otherwise an empty set fails with `ING6203 EmptyInstanceSet`. Mates and interference address members by key, and MEC's `fasten` returns a set.

**Decision D-ING-22:** Existence of an Instance or Instance set depends only on `#[configuration]` parameters and constants, checked at compile time; a set's members and count may depend on any value. *Why:* the 150% BOM needs static existence (R3-18), and one fastener per resolved hole needs a computed count (R8-20, R9-16). *Rejected:* `options` and `when` keywords; enumerating configurations (exponential); a configuration count checked against the holes (two edits per hole). (revised in round 3)

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

A `CatalogSelection` is a pure function over pinned definitions, plus pinned offers when it ranks by price or stock (ELX); `crucible update parts` refreshes only the pins. `?` turns `NoCatalogMatch` into a failure whose fixes are the nearest candidates, and editing `speed` re-evaluates only `bearing_speed`.

A feature's parameter list is a record type, `Params<f>`, and a call spreads a record into named arguments. A design table is a table of parameter records (D-MEC-10):

```
let b = bracket(..heavy, width: 90mm)                     // later arguments override the spread
pub let brackets = family(bracket, key: |r| r.item, rows: table {
    item     | width | thickness     | load
    "BR-060" | 60mm  | 4mm ± 0.1mm   | 1.2kN
})
```

A row's type is `{ item: String, ..Params<bracket> }`. `table("brackets.csv")` reads a repository file whose header names units (`width [mm]`), and a mismatched cell fails with `ING3501 UnitMismatch { column, expected }`.

### Patterns, loops and keys

A pattern is a feature whose instances differ only in their keys, and a `for` loop yields a list. Iteration contributes keys, never positions (contract section 5):

- iteration over entity lists or resolved queries keys by `EntityId`;
- MEC's generators return keyed lists (`linear` by `(i, j)`, `circular` by angular index, `at_points` by anchor, and so on);
- integer ranges and literal lists keep integer keys, and `keyed(xs, by: f)` keys any list, failing with `ING6202 DuplicateKey` on a repeat;
- `ING-L-PositionalKey` warns when a computed list whose length depends on geometry is iterated by position.

Pattern `skip:` lists take keys (MEC). `fold` and `scan` carry running state, since there is no mutable accumulator.

```
let vents  = pattern(vent_slot(length: 10mm), at: linear(dir: +x, count: 8, spacing: 6mm))
let graded = for i in 0..8 { vent_slot(length: 10mm + i * 2mm) |> move(x: i * 6mm) }
```

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Kiln-held values and Booleans | Handles compared by `ObjectId`, geometry by `GeometryId`; n-ary lowering by a fixed rule | `ING6701` | ING-O-1 | 0 |
| Text-derived `CallSite` | Frames of statement, call and keys; `#[was]` renames | `ING1102`; `ING-L-RepeatedStage` | ING-O-25, ANV-O-SITE-1 | 0 |
| Label invariance in the language | No order, numeric hash or printing of names; label-free seeds | Not expressible | ANV-O-LABEL-1 | 0 |
| Copies and placements | Transforms keep names; colliding operands relabelled in program order | — | ANV-O-COPY-1 | 1 |
| Queries | Canonical plans resolved by `anvil::resolve`; anchored ranks; extent-use acceptances; kinded roles | `ResolveError`; `ING4103`, `ING5001`, `ING5002` | ING-O-11, ANV-O-NAME-2 | 1 |
| Builder blocks and sketches | `Builder<I, Ctx>`; symbolic entities; certified solved points; inline seeds | `ING1104`, `ING2301`, `ING2402` | ING-O-5, ING-O-10, ING-O-23, ANV-O-NAME-5 | 1 |
| Variant regions | Instance existence from configuration parameters and constants only | `ING2601` | ING-O-30 | 1 |
| Instance sets | Static existence; evaluated members keyed by anchors; `min: 0` | `ING2601`; `ING6203` | ING-O-30 | 2 |
| Catalog selections | Pure over pinned data; re-resolve on argument change | `NoCatalogMatch` with candidates | ING-O-13 | 2 |
| Families and tables | Record spread, table literals, CSV with unit headers | `ING2105`, `ING3501` | MEC-O-PF-12 | 1 |
| Keyed iteration | Keys from entities, generators, ranges and `keyed` | `ING6202`; `ING-L-PositionalKey` | ING-O-26 | 1 |

## Evaluation

### Calls and effects

Every Ingot call is pure; calls differ in cost and in whether Kiln memoizes them, as their declarations show. A `feature` may return any type and is the unit of history and caching; a `fn` is not.

| Call kind | Declared with | Kiln node |
| --- | --- | --- |
| Function | `fn` | None; the executor calls it directly |
| Memoized function | `#[memo] fn` | Keyed by code hash and arguments only; may not call operations or features (`ING2501`) |
| Feature | `feature` | Feature node, keyed with its `CallSite` |
| Operation | `extern fn` with `#[op("anvil::blend")]` | Op node keyed by `OpKey` |
| Wasm component export | `extern fn` with `#[component(…)]` | Op node whose implementation is the Wasm component |
| External Op | `extern fn` with `#[external(…)]`, declared by its package (ECO) | Op node on untrusted-evaluation workers (contract section 7.8) |
| Query resolution | Implicit where a `Query` reaches an operation | Resolve node |
| Check | `require` | Check node |

Operations, Wasm component exports and External Ops are the only engine effects: pure in meaning, expensive, asynchronous and cached. `ingot-bindgen` generates `std::ops::anvil` and `std::ops::flux` from the operations catalogs, and any package may write `extern` declarations checked against them (`ING8001`). Source never names a behavior version; `ingot.lock` pins one per operation.

std chooses each helper's kind by one rule, checked by the lint `ING-L-FeatureKind`. A helper that calls an entity-naming operation or returns `EntityId`s is a `feature`. A pure one estimated above 10⁶ steps is a `#[memo] fn`, and any other is a `fn`.

**Decision D-ING-10:** Ingot has no user-visible effect system: operations are pure calls, and side channels (checks, notes, tolerance sites, PMI) are write-only accumulators in canonical call-site order, like Salsa's. *Why:* effect annotations would describe effects the language forbids, and canonical order makes accumulators independent of evaluation order. *Rejected:* effect rows (nothing to track); FeatureScript-style `context` and `id` threading (boilerplate).

### Determinism and randomness

Contract section 7.3 owns the determinism rules, PLT the mechanisms, and KLN the policy and random-stream keys (contract section 7.2). Ingot adds these language rules:

- strict left-to-right evaluation, checked `Int` overflow, and no NaN or infinity values (`ING6102`);
- ordered maps and sets, stable sorts, and no `Real` map keys (`q.key(resolution: 1um)` quantizes);
- NFC strings without locale; nothing ordered or hashed by name; labels invisible to code, since Kiln joins them;
- no time, environment, files or network: sources, tables, Assets and External inputs are Kiln input cells read by content.

Randomness is a value. `Rng` keys Philox, Salmon and colleagues' counter-based generator, as Philox-4×32-10, which carries three rounds of safety margin. The n-th number is a pure function of key and n, so streams split and run in parallel without changing any value.

```
let rng = Rng::new(seed).split("pins")                 // seed: an explicit parameter, never ambient
let u = rng.uniforms(count, of: 0.0..1.0)
```

std's samplers (`sobol`, `latin_hypercube`, `normal`) take an `Rng`. `Seed::from(x)` hashes `x` without names (a Body by `GeometryId`), so MEC's scramble seeds stay label-invariant; `rng.seed()` passes a 64-bit seed to a Wasm component.

### Failures and Aborts

A `Failure` is a deterministic, typed value saying why a computation produced no result: a fillet radius too large, a query split, `OpVersionRetired`. It propagates to the nearest `try`, which turns it into `Result<T, Failure>`, or becomes the enclosing feature call's result. Kiln caches it like any value, and dependents that need it fail with `DependencyFailed { upstream }`.

```
let rounded = match try body |> fillet(edges, r) {
    ok(b) => b,
    err(BlendError::RadiusTooLarge { max }) => body |> fillet(edges, 0.95 * max),
    err(e) => fail(e),
}
```

`Failure` is an extensible union, like OCaml's extensible variants. Every enum implementing `Error` adds its variants, and a match over `Failure` needs a wildcard arm. An `Undecided` value from control flow is not a `Failure`, and `try` cannot catch it.

An `Abort` is environmental: cancellation, resource or budget exhaustion, device or worker loss, or Kiln's evaluation-wide limits (contract section 2). `try` cannot observe it, and no node that observed one writes a memo entry, CAS object or attestation (contract section 7.2).

**Decision D-ING-11:** Deterministic failures propagate to the nearest `try` or feature boundary and are cached there; Aborts are not values, and no Ingot construct observes them. *Why:* `?` on every geometry call is noise, and a fallback taken because a worker ran out of memory would be cached as geometry (R3-03). *Rejected:* `Result` on every operation; untyped exceptions; catching every failure kind, the round 1 rule. (revised in round 2)

A feature's checks are evaluated against its result; when the feature fails, they report `Error(DependencyFailed)`. A failure inside one Instance never erases sibling work.

### Limits

Per-call limits are counted in units the language defines, with the cost table in the language behavior version. Outcome names follow KLN's catalog of limit outcomes.

| Limit | Unit | Default per feature call | Failure |
| --- | --- | --- | --- |
| Fuel | Steps of the cost table | 10⁹; `#[fuel(…)]` raises it up to the manifest maximum | `ING6301 FuelExhausted` |
| Call depth | Ingot frames | 2,048 | `ING6302 StackExhausted` |
| Memory | Semantic bytes: 8 per scalar or handle, 16 per collection header | 1 GiB | `ING6303 MemoryLimit` |
| Operation calls | Count | 10⁶ | `ING6304 WorkLimit { kind: OperationCalls }` |
| Symbolic expression size | DAG nodes | 10⁷ | `ING6305 WorkLimit { kind: ExpressionSize }` |

A call's steps include the plain functions it calls, while feature and `#[memo]` calls are nodes with their own limits. An outcome therefore never depends on the caller's remaining budget or the cache. An operation call charges 100 steps plus 1 per marshalled element. Effective limits come from source and manifest only and enter the node key.

Kiln adds two evaluation-wide limits as Aborts. Nested demands stop at 10,000, so `f(n) = f(n + 1)` aborts with `DemandDepthExhausted`, and a per-Evaluation fuel governor ends in `BudgetExhausted`. An organization ceiling below a requested limit refuses the Evaluation at admission with `FuelCeilingExceeded`, and a host out of memory raises `ResourceExhausted`.

**Decision D-ING-23:** Per-call limits come from source and manifest only and enter the node key; evaluation-wide limits and policy ceilings act only as Aborts. *Why:* a policy-clamped limit made two organizations cache different results for one key (R3-12), and per-call limits alone allowed unbounded node chains (R3-04). *Rejected:* ceilings inside the limit; per-call limits as the only bound; wall-clock limits (nondeterministic).

`#[suppressed]` on a `let` removes the call: a pipeline statement whose input and output types agree binds its input, and other uses fail with `ING6601 Suppressed`. Rollback is the request `EvalRequest { target, until: statement }`, never a source edit.

### The Ingot IR and Kiln

Lowering produces the Ingot IR (IIR), a dataflow graph in the style of the RVSDG, whose "regions capture the hierarchical structure of programs". Ingot is pure, so the IIR has no state edges.

| IIR construct | Meaning |
| --- | --- |
| Simple node; Kiln call node | Plain computation; an Op, resolve, feature or check call with its `CallSite` |
| γ, map and fold, λ and φ regions | Conditionals; loops carrying keys; functions and recursive groups |
| Observation edge | Where the executor needs a Kiln-held value's content |

Spans live in a side table, so an edit above a function leaves its IIR unchanged. Each module's code hash is a SHA-256 Merkle hash over its IIR and the code hashes of the modules it uses.

1. **Front-end nodes.** A module's front end is keyed by its source hash, the language behavior version and its imports' interface hashes. Its outputs are the IIR, identified by the module code hash, and diagnostics, also keyed by the compiler release. Releases emit bit-identical IIR for one language behavior version (ING-O-1), so IIR is shared across releases. Its stages backdate, so a comment edit stops at the IIR.
2. **Feature nodes.** A feature call's key follows contract section 7.2, adding its `CallSite` and effective limits. Its value splits into outputs with their own change markers: the result, one per accumulator kind, and metadata (fuel, cost). Metadata never enters backdating, so a fuel-only edit re-executes nothing downstream.
3. **Asynchronous calls.** The executor issues each Kiln call, receives a pending handle at once and suspends only at observation edges. Independent calls therefore run in parallel, and Kiln prefetches calls known before any observation.
4. **Program order.** Each call records its program-order index. When several calls fail, the outcome is the earliest in program order, and speculative work after it never changes a result. Anvil's copy relabelling reads the same index.
5. **Overrides.** A request may carry literal overrides keyed by `LiteralSite` (statement identity, call identity, argument slot). Kiln treats them as input cells, and a node's key includes the overrides in its own code. Results computed under overrides never enter the shared cache (KLN), and a wrongly typed override fails with `ING6502`.

Drags stream overrides through AGT's `edit.stream` and `evaluate.subscribe`, on PLT's `Interactive` pool lane. An override's `LiteralSite` follows `#[was]`, so a concurrent rename of the binding keeps the drag alive. Only deleting the literal ends the drag, with a notice (UIX).

[[DIAGRAM diagrams/01-ingot-pipeline.jsx: Ingot pipeline · front end, executor and Kiln]]

Read the diagram left to right: the front end turns source into IIR, the interpreter hands each call to Kiln as a pending handle, and values return at observation edges.

### Fidelity, drags, holes and derivatives

Ingot code cannot observe fidelity, so every fidelity runs the same program; a check's `fidelity:` names the fidelity of its own node. A release demands every node at `SignOff`, geometry included. Anvil decides topology alike at every fidelity (contract section 7.1). A query, fix or seed written at `Interactive` thus resolves alike at `SignOff`, unless that fails with `Ambiguous`.

When a drag starts on a literal, Ingot compiles a residual program over the literal's forward slice, with everything else constant; its outputs equal the full program's (ING-O-12). Unfinished code becomes typed holes that evaluate to `ING6001 Incomplete`, and evaluation proceeds around them as in Hazel.

Derivatives serve UIX's edit plans and Flux's `grad(J, wrt: [p1, p2])`. Data dependence plus provenance gives the literals that can affect an entity, exactly and cheaply. Forward mode uses dual numbers and each Op's tangent rule, reverse mode Kiln's `Differentiable` operations (KLN); an Op without a rule fails with `NotDifferentiable { op }`.

In phase 1, edit plans rank by provenance first: the literal of the call whose `CallSite` and role created the dragged entity. IIR dependence distance comes next, and derivatives refine the ranking from phase 2, when `anvil::shape_velocity` lands.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Calls and accumulators | Eight call kinds; canonical accumulators as separate outputs | `ING2501`, `ING8001`; `ING-L-FeatureKind` | ING-O-13 | 0 |
| Determinism and randomness | Bit-identical values, failures and fuel; keyed Philox streams | Aborts never cached | ING-O-1, ING-O-6 | 0 |
| Failures and Aborts | `try` catches `Failure` only; Aborts write nothing | Typed `Failure`; `DependencyFailed` | ING-O-1, ING-O-24 | 0 |
| Per-call limits in keys | Limits from source and manifest; ceilings at admission | `ING63xx`; Abort `FuelCeilingExceeded` | ING-O-28, ING-O-6 | 0 |
| Evaluation-wide limits | Demand depth and fuel governor as Aborts (KLN) | Abort `DemandDepthExhausted` | ING-O-24 | 0 |
| IIR and the Kiln contract | Front-end keys; IIR shared across releases; split outputs; pending handles; program order | `DependencyFailed` | ING-O-1, ING-O-13, ING-O-27 | 0 |
| Literal overrides | Keyed input cells; never in the shared cache; follow `#[was]` | `ING6502` | ING-O-12 | 1 |
| Suppression and rollback | Binding takes the pipeline input; rollback as a request | `ING6601` | ING-O-10 | 1 |
| Drag specialization | Residual program on the forward slice | Falls back to full evaluation | ING-O-12 | 1 |
| Holes | Evaluation around holes | `ING6001` | ING-O-15 | 1 |
| Derivatives | Dependence and provenance ranking (1); forward and reverse modes (2) | `NotDifferentiable { op }` | ING-O-16 | 1, 2 |

## Diagnostics and checks

### Diagnostics

Compile-time diagnostics and evaluation failures share one structure for the UI, the CLI and agents.

```rust
pub struct Diagnostic {
    pub code: Code,                        // "ING3001"; other subsystems use their own prefixes
    pub severity: DiagnosticSeverity,      // Error | Warning | Info | Hint
    pub message: String,                   // one sentence: what is wrong and why
    pub primary: SourceSpan,
    pub labels: Vec<(SourceSpan, String)>, // secondary spans
    pub notes: Vec<String>,                // the rule, linked to its catalog page
    pub fixes: Vec<Fix>,                   // ranked
}
pub struct Fix { pub title: String, pub edits: Vec<SourcePatch>, pub applicability: Applicability }
pub struct SourcePatch { pub path: SourcePath, pub range: TextRange, pub expected: Sha256, pub replacement: String }
```

`Applicability` is `MachineApplicable`, `MaybeIncorrect` or `HasPlaceholders`, and `SourcePatch` is the record AGT's edit methods take. Query fixes carry Anvil's sampled stability evidence (ANV).

| Codes | Area | Examples |
| --- | --- | --- |
| ING0xxx | Lexing and parsing | `ING0002` non-NFC source; `ING0003` hidden characters |
| ING1xxx | Names and modules | `ING1001` unknown name; `ING1103` duplicate check identity; `ING1104` builder name clash |
| ING2xxx | Types and traits | `ING2001` mismatch; `ING2402` branch on a symbolic value; `ING2601` Instance or Instance set under a computed condition |
| ING3xxx | Units and kinds | `ING3001` dimensions; `ING3002` kinds; `ING3201` affine misuse |
| ING4xxx | Tolerances and GD&T | `ING4101` comparison of tolerances; `ING4201` material condition on a non-size aspect |
| ING5xxx | Geometry references | `ING5001` positional entity access; `ING5002` role on the wrong entity kind |
| ING6xxx | Evaluation failures | `ING6001` incomplete code; `ING6203` empty Instance set; `ING6401` undecided branch |
| ING7xxx | Packages and lockfile | `ING7001` unresolvable dependency |
| ING8xxx | Bindings | `ING8001` extern signature differs from the catalog |
| `ING-L-<Name>` | Lints | `ING-L-FragileSelector`, `ING-L-RepeatedStage`, `ING-L-HertzPhase`, `ING-L-SharedSymbol` |

Every code has a generated catalog page with a triggering example and each fix, compiled in CI. A `MachineApplicable` fix must compile and remove its diagnostic (ING-O-9). The canonical example's unit error reads:

```
error[ING3001]: cannot add Length and Force
  --> bracket.ingot:14:17
14 |     let x = width + load
   |             ----- ^ ---- Force (kg·m/s²), declared at 11:5
   |             Length (m), declared at 9:5
   = fix (maybe incorrect): convert load with a compliance: `width + load * compliance`
   = fix (has placeholders): compare instead: `width < ?`
```

An evaluation `Failure` adds the feature call chain, the entities involved and an optional cause. Anvil's and MEC's fixes arrive as `Fix` values naming the design's own bindings (contract section 7.2), and the interpreter reports the exact failing expression.

### Checks

`require` declares a check: a predicate with a severity, a fidelity, the weakest bound kind that may decide it, and a source. It never changes the value it attaches to, and it runs as a separate node after the geometry it reads.

```
require stress < 0.6 * sy, severity: Error, fidelity: SignOff, decides_on: Estimated,
        name: "static_margin", because: "allowable of 0.6 Sy for this bracket class"
part.require(part.mass() < 120g, severity: Warning)       // attaches to the Part and returns it
```

| Field | Default | Meaning |
| --- | --- | --- |
| `severity` | `Error` | Only an `Error` check can fail the gate predicate; `Warning` and `Info` report |
| `fidelity` | `SignOff` | The fidelity a gate evaluates; lower outcomes are provisional |
| `decides_on` | `Estimated` | The weakest bound kind that may decide: `Estimated` or `Guaranteed` |
| `name` | none | Joins the `CheckId` when written |
| `because` | none | Rationale for reports and agents |

A check's identity is its `CheckId` (contract section 5): the attachment's `CallSite` or Instance path, the `require` statement's identity, and the `name` if written. It never derives from predicate text, so editing a limit keeps the verdict history and Evidence records. A check declared twice on one attachment fails with `ING1103`, whose fix adds `name:`.

A `require` statement attaches to its feature call, a module-level one to the design, and `x.require(…)` to `x`, under the Instance path in assemblies. A comparison chain records value, limit and margin, and a conjunction one sub-outcome per conjunct.

The outcome is contract section 5's `CheckOutcome`, with its confidence and `evidence_records`. When only non-discretization parts are `NotQuantified`, a `Pass` lists them in `conditional_on`, and a `Fail` stays `Fail`. A policy allowance (KLN) covering each listed source re-evaluates the check with it as a declared `Estimated` part; without one the verdict is `Undecided { Unquantified(sources) }`.

ING owns the gate predicate, which KLN and AGT apply at protected merges, Proposals and releases. A check meets a gate when its severity is below `Error`, or a Waiver covers it. Otherwise it needs a non-provisional `Pass` in a platform class the gate accepts, with every `conditional_on` source covered by an allowance.

A `require` under the protected `oracles/` directory has the source `Protected(path)`, which agents cannot edit; every other check has `Declared(span)`. `#[waive(reason:, until:)]` on a `require` statement, or with `check:` naming a full `CheckId`, only requests a Waiver. It counts nowhere until an authorized human signs a matching Waiver record (contract section 2). Agents may write the attribute, never the record, and `Protected` checks accept none.

When no study estimates a check's functional, the language service offers a visible fix adding it to the study's `goals:` (D-FLX-5).

```
use std::sim::quick::static_stress

pub feature bracket_check(b: Part, clamp: Query<Face>, pad: Query<Face>, load: Force = 1.2kN) -> Part {
    let study = static_stress(b, fixed: clamp, force: load, on: pad)
    let peak = study.von_mises.max(over: b.away_from([clamp, pad], 8mm))   // Approx<Stress>
    b.require(peak < 0.6 * b.material.yield_strength(at: 20degC), name: "static_margin")
}
```

`away_from(sets, d)` excludes each set by `d`; without `d`, each flagged set's default distance applies (FLX).

| Situation, with an illustrative yield enclosure of 240 MPa to 276 MPa, so a limit of 144 MPa to 165.6 MPa | Outcome of `static_margin` |
| --- | --- |
| `Preview` result | `Undecided { Indicator }` |
| `Interactive`: 112 MPa ± 20 MPa `Estimated`; model form `NotQuantified` | Below 144 MPa: a provisional `Pass { conditional_on: [model form] }` |
| `SignOff`: 118 MPa ± 1.5 MPa, confirmed by one refinement | `Pass { conditional_on: [model form] }` at confidence 0.99 |
| Same, with a policy allowance citing a design-code partial factor | `Pass`, meeting the gate |
| The refinement's value falls outside the first bound | `Undecided { CalibrationUnconfirmed }` |
| The result lies outside its calibration class's envelope | `Undecided { Indicator }` |
| A flagged singular set inside the region, not excluded by its distance | `Undecided { SingularPoint }`, with fixes to exclude it or add a fillet |
| The solve does not converge | `Error(failure)`, with the solver's diagnostics |

**Decision D-ING-12:** Checks are declarations evaluated as separate nodes: a failing or undecided check never stops geometry, and no feature branches on a check's outcome. *Why:* designers need to see failing geometry, expensive predicates run later at lower priority, and adding a check never changes a design or a solve (D-FLX-5). *Rejected:* aborting assertions (hide the geometry); checks as Booleans in the dataflow (could alter geometry).

### Free text

The lossless tree classifies every span as free text or structure. Comments, string literals, description templates and identifiers neither compiled nor typed by a human are free text. `repo` records the integrity of the context that wrote each span (KLN).

Every value evaluated from a free-text span, such as a part name, a drawing note or embossed text, carries that span's integrity into its node's label. `api` returns such strings, like untrusted spans themselves, as `ExternalText` handles (contract section 7.6). A merge endorses structure and typed values, never free text; per-span endorsement shows the text verbatim.

**Decision D-ING-24:** Every span is free text or structure; merging endorses only structure, and values evaluated from free text keep its integrity. *Why:* an agent could address a later reader through a merged comment (R5-02) or a literal evaluated into a part name (R11-02). *Rejected:* wrapping only imported strings, the round 1 rule; banning agent comments (they document intent); integrity on spans only, the round 2 rule. (revised in round 3)

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Diagnostics and fixes | One structure; ranked `SourcePatch` fixes; catalog pages | A failing machine-applicable fix is a defect | ING-O-9 | 0 |
| `require` and outcomes | `CheckOutcome`; `CheckId`; conditional `Pass`; protected sources | `Error(Failure)`; `Undecided`; `ING1103` | ING-O-8, ING-O-27 | 1 |
| Gate predicate | Severity, a covered non-provisional `Pass`, or a Waiver record | Gate refused with the failing checks | ING-O-38 | 1 |
| Check independence | Adding or removing a check changes no other node's key | — | ING-O-27 | 1 |
| Free-text spans | Classified spans; handles for untrusted authors; integrity carried into evaluated strings | `ING0003` | ING-O-32 | 1 |

## Execution

Until the code generator ships, the reference interpreter is the only Ingot executor on every target (contract section 7.4). Written in Rust, it interprets the IIR in the canonical class with `detmath`, checking non-finite values, fuel and depth after every step. Heap frames let a call suspend without stack switching. One interpreter per worker holds every suspended call in its own allocator region.

| Measure | Target | Benchmark |
| --- | --- | --- |
| Interpreter time per GP1 feature body, operations cached | ≤ 200 µs on the reference laptop; ≤ 600 µs in browsers | `ingot-bench` on GP1 |
| Ingot share of a golden-product rebuild | ≤ 2%, else the code generator enters | GP1 and GP2 rebuilds |
| Suspended feature calls | 500 within 256 MiB of the browser engine worker | Golden-product evaluations |
| Front-end re-check of an edited 2,000-line module | Under 30 ms | Edit-replay corpus |
| Drag residual program per frame, operations excluded | Under 1 ms | UIX drag scripts |
| Numeric Ingot against idiomatic Rust, once compiled | ≤ 2.5× natively; ≤ 4× in browsers | `ingot-bench` numeric programs |

All figures are targets. Until the code generator exists, heavy numeric loops go to operations or Wasm components.

**Decision D-ING-13:** The canonical-class interpreter is the only Ingot executor until `ingot-bench` shows Ingot above 2% of a golden-product rebuild; then a code generator to WebAssembly core modules enters, phase 2 at the earliest. *Why:* phase 1 needs only orchestration speed, and a second executor would sit on the critical path with no gate need (R6-25). *Rejected:* the code generator in phase 1; Cranelift native code (no browser path); Ingot to Rust (a run-time toolchain); LLVM (slow, no browser target). (revised in round 2)

The interpreter stays for cold start, debugging, replay and differential testing. The code generator emits one module per compilation unit with a source map, run by Wasmtime with Cranelift natively and by each browser's engine. Its modules pass the determinizer's verification (contract section 7.4), and ING-O-1 checks their fuel accuracy.

Its optimizer never reassociates or contracts floating point, and it keeps every operation that can fail in program order. It charges fuel computed on the canonical IIR and never merges, duplicates or reorders Kiln calls. Suspension lowers to resumable state machines, since Wasmtime's tier documentation lists stack switching as unsupported by Cranelift on aarch64.

Each worker keeps one instance with per-call allocator regions, and user modules replace the interpreter at the next feature call boundary, unobservably.

**Decision D-ING-14:** Plain values use reference counting with in-place update of uniquely referenced lists and records, Perceus-style in the code generator. *Why:* immutable, strict values are acyclic, Perceus is "garbage free" with "guaranteed in-place updates", and prompt freeing keeps loops within the memory limit. *Rejected:* a tracing collector (pauses in a drag frame); an arena per feature call (late freeing); ownership types for users (ceremony). (revised in round 2)

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Reference interpreter | Canonical class; checks after every step; heap frames | Abort `ResourceExhausted` | ING-O-1, ING-O-33, ING-O-34 | 0 |
| Code generator | Verified deterministic Wasm subset; state machines; Perceus | Rejection is a compiler defect | ING-O-1, ING-O-14 | 2 at the earliest |

## Rust features and Wasm components

Features may be written in Rust as Wasm components when ECO's tier rule (D-ECO-6) says so. `#[ingot::feature]` writes the WIT world, the glue and a typed Ingot wrapper, and a build fails if a checked-in artifact differs from its regeneration.

```rust
use ingot_sdk::{Cx, Body, Length, Angle, Plane};

/// Involute spur gear tooth profile, closed, centered on the origin.
#[ingot::feature(package = "acme::gears", category = "Power transmission", icon = "gear")]
pub async fn involute_profile(
    #[ingot(range = "0.1mm..=50mm")] module: Length,
    #[ingot(range = "6..=400")] teeth: u32,
    #[ingot(default = "20deg", range = "14.5deg..=30deg")] pressure_angle: Angle,
    cx: &mut Cx,                                                     // the guest context
) -> Result<Body, GearError> {
    let mut s = cx.planar_builder(Plane::XY, cx.site("profile"));  // explicit, stable call key
    for i in 0..teeth {
        s.add_spline(cx.site_keyed("flank", i), &flank_points(module, pressure_angle, i)?)?;
    }
    s.finish_region().await.map_err(GearError::from)              // one crucible:ops call
}
```

`ingot-bindgen` generates the guest SDK, `ingot_sdk`, from the `crucible:ops` and `crucible:host` imports. Its `Cx` is the only context a `#[ingot::feature]` function receives. `OpCx` stays native-only, because it wraps runtime handles that an out-of-process component cannot hold (KLN, PLT).

| `Cx` method | WIT import | Failure |
| --- | --- | --- |
| `site(name)`, `site_keyed(name, key)` | None; appends a call key to the call's `CallSite` | `ING8201` on a duplicate key |
| Builders and operation calls (`planar_builder`, `anvil()`, `flux()`) | `crucible:ops/anvil`, `crucible:ops/flux`, asynchronous (contract section 7.4) | The operation's typed `Failure` |
| `seed()` | None; the call's `seed: u64` argument | — |
| `diagnostic(…)` | `crucible:host/diagnostics` | — |

The SDK's quantity types come from the prelude's kind table, so dimensions survive in Rust. `ingot-bindgen` emits `GearError` as an Ingot enum implementing `Error`, with the codes and fixes declared in Rust.

| Rule | Mechanism |
| --- | --- |
| A Wasm component call is an Op keyed by the determinized binary's hash, export and arguments | Pinned in `ingot.lock` (ECO) |
| Evaluation worlds import no WASI; randomness arrives only as a `seed: u64` argument from an `Rng` | Contract section 7.4 |
| Operation calls go through `crucible:ops` as recorded Op dependencies; engine data arrive only through handles from the inputs | Contract section 4 |
| Every operation call and created entity takes a call key appended to the call's `CallSite`; duplicates fail with `ING8201` | Stable `EntityId`s |
| Fuel is metered by the determinizer and limited by the wrapper's `fuel:` | Deterministic limits |
| Traps, `FuelExhausted`, `StackExhausted` and `MemoryLimit` are cached `Failure`s; host-caused growth failures and resource loss are Aborts | Contract sections 7.2 and 7.4 |
| Error estimates map to `Approx` values or `ErrorBudget` parts; `outside-envelope` to the validity flag | Wrapper convention |
| Diagnostics attach to the call's span in emission order; Wasm component strings become `ExternalText` | Write-only accumulator |
| The wrapper is the public interface; the raw `extern fn` is `pub(package)` | One typed signature |

| WIT | Ingot |
| --- | --- |
| `bool`, `s8` to `s64`, `u8` to `u32`; `u64` | `Bool`, `Int`; `u64` fails with `ING6101` above 2⁶³ − 1 |
| A `u64` named `seed`; a `fidelity` enum | `Seed`; omitted and filled by the host |
| `f32`, `f64`; `crucible:units` aliases | `Real`; `Length`, `Force`, `Temperature` (kelvin, converted in the wrapper) |
| `string`, `list`, `option`, `result`, `tuple` | `ExternalText` for Wasm component strings; `[T]`, `Option`, `Result`, tuples |
| `record`, `variant`, `enum`, `flags` | `record`, `enum`, `enum`, `Set<Enum>` |
| Body and Field resources; other resources | `Body`, `Field<D, V>` handles; opaque handles owned by the wrapper |

A bare `f64` parameter becomes `Real` with `ING8101`, asking for a unit alias in `ingot-bindgen.toml`. A Rust feature is an opaque debugger frame, and it has a forward derivative only when `#[ingot::feature(tangent = …)]` names an exported tangent.

**Decision D-ING-15:** `#[ingot::feature]` generates the WIT world, glue and typed Ingot wrapper from one Rust signature, whose function receives the generated guest context `ingot_sdk::Cx`. *Why:* one signature carries units and ranges to the type checker and dialogs, and an out-of-process component needs a context made of imports (R9-19). *Rejected:* hand-written WIT and wrappers (drift); native Rust plugins (unsafe, no browsers); passing `OpCx`, the round 2 example. (revised in round 3)

A package calls a Wasm component through the same generated binding, and the component's declared error estimate becomes a statistical `ErrorBudget` part, `Guaranteed` only if declared so.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `#[ingot::feature]` | One Rust signature generates WIT, glue and wrapper | Artifact drift fails the build; `ING8xxx` | ING-O-17 | 1 |
| Guest SDK | `ingot_sdk::Cx` generated from the WIT imports; asynchronous operation calls | `ING8201`; typed `Failure`s | ING-O-17 | 1 |
| Wasm component calls | Ops keyed per contract section 7.2; call keys; metered fuel | Typed `Failure`s; Aborts | ING-O-1, ING-O-17 | 1 |
| Binding generation | WIT to Ingot with units | `ING8101`, `ING8102` | ING-O-17 | 1 |

## Packages and versions

A package is a directory with `ingot.toml` and modules under `src/`, rooted at `src/lib.ingot`. A design repository's root is `src/main.ingot`, whose `pub` items are its outputs. Items are private, package-wide with `pub(package)`, or public with `pub` and part of the semantic-version interface.

A `use` path starts with a dependency, `package`, `self` or `super`. Imports are acyclic (`ING1301`), as in KCL, and two globs supplying one name are ambiguous (`ING1201`).

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

The registry refuses a minor or patch release that breaks the public interface (ECO); Ingot defines "breaks":

| Change | Release |
| --- | --- |
| Remove or rename a public item, parameter, field, role or coordinate system; change a parameter's dimension, kind or type; add an undefaulted parameter; narrow a range; extend an exhaustive enum | Major |
| Change a default value, or the entity names a public feature produces on the package's test designs | Minor, labelled output-changing (D-ECO-14) |
| Add a defaulted parameter, an item, a role or a variant to a `#[non_exhaustive]` enum; widen a range | Minor |
| Change test-design outputs through private code, keeping entity names | Patch, labelled output-changing (D-ECO-14) |
| Change only documentation, metadata or private code, leaving outputs and names unchanged | Patch |

`ingot.lock` is sorted TOML written only by tools. ING owns `[language]`, the language behavior version fixing evaluation semantics, the IIR lowering, the cost table, the n-ary lowering rule and std numerics. `[operations]` pins operation versions (KLN and the owners), and `[[package]]`, `[[asset]]` and `[[external]]` pin the rest by SHA-256 (ECO). Compiler releases may change diagnostics and speed, never IIR, values, failures or fuel.

**Decision D-ING-16:** The lockfile pins a language behavior version beside the operation versions, and a toolchain implements every language behavior version in its support window. *Why:* an old design must rebuild identically, and fuel costs and std numerics are part of its result. *Rejected:* pinning the toolchain release (old toolchains kept runnable forever); letting editions carry behavior (ECO's D-ECO-23 forbids it).

Resolution uses PubGrub, which can "explain errors more clearly than the alternatives": `ING7001` carries its derivation and relaxations as fixes. Two major versions of a package may coexist; passing a value between them fails with `ING7201`.

A module is the unit of a source label, and front ends read only their imports' signatures, so an uncleared principal compiles against a declassified signature (contract section 7.1).

Editions follow Rust's model and D-ECO-23: they change surface syntax, the prelude and lint defaults, never behavior. `crucible migrate` applies machine-applicable fixes and rejects any item whose IIR changes beyond spans. Rust's guide notes that "Cargo's automatic migrations aren't perfect", and the IIR check makes Ingot's exact.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Modules and visibility | Three levels; acyclic imports | `ING12xx`, `ING1301` | ING-O-5 | 1 |
| Semantic-version rules | The table above, including entity-name changes | Publish refused (ECO) | ING-O-18 | 1 |
| Lockfile and behavior versions | `[language]` pinned; releases never change IIR or values | A changed value is a defect | ING-O-1, ING-O-18 | 1 |
| Resolution | PubGrub with explanations; two majors coexist | `ING7001`, `ING7201` | ING-O-18 | 1 |
| Editions and migrations | IIR-preserving rewrites only | Non-preserving rewrites listed, not applied | ING-O-19 | 2 |

## Feature metadata and dialogs

A feature's signature generates its dialog, documentation page and agent tool schema; attributes refine them.

| Source element | Generated UI |
| --- | --- |
| Quantity parameter | Numeric field with unit, accepting expressions (UIX) |
| `Tol<T>` parameter, or a toleranced default | Value field with a tolerance sub-field |
| `Bool`; `enum` | Toggle; segmented control up to five variants, else a dropdown |
| `Query<K>` | Selection field showing the query, filtered by `K` |
| `Material`, catalog part types | Pickers bound to the material library and the catalog |
| `Option<T>`, record, `[T]` | Enable toggle; group; list editor |
| `in` range; doc comment | Field and slider bounds checked at evaluation (`ING6501`); help text |

| Attribute | Meaning |
| --- | --- |
| `#[feature(category:, icon:, handles:)]` | Toolbox placement, icon, manipulator handles (UIX handle kinds) |
| `#[ui(group:, advanced, visible_if:, step:, filter:, label:)]` | Grouping, disclosure, visibility, slider step, selection filter, label |
| `#[roles(…)]`, `#[fuel(…)]`, `#[example]` | Created roles per entity kind; a raised fuel limit; a compiled, evaluated doc example |
| `#[deprecated(since:, instead:)]`, `#[removed(in:, instead:)]` | Lifecycle with fixes |

`visible_if` takes a pure closure over the parameter record, evaluated by the interpreter as values change. FeatureScript expresses the same with `if` statements in a `precondition` block.

**Decision D-ING-17:** Dialogs are generated from signatures, types, doc comments and a small attribute vocabulary; there is no dialog language. *Why:* one declaration serves dialog, docs, semantic-version checks and tool schemas without drift, and Onshape shows generated dialogs work at scale. *Rejected:* FeatureScript-style precondition blocks (a second statement language); hand-built dialogs (drift).

`crucible doc` generates reference pages; every `///` code block compiles, and `#[example]` blocks evaluate in CI with their checks. A public item without a doc comment fails the registry's coverage gate (ECO).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Dialogs from signatures | Types and attributes to fields, groups, handles and visibility | `ING6501` out of range | ING-O-20 | 1 |
| Documentation | Compiled and evaluated examples; coverage gate | Publish refused (ECO) | ING-O-20 | 1 |

## Tooling

### Lossless tree and blocks

`ingot-syntax` parses into a lossless green-red tree in rust-analyzer's design, with the `rowan` crate (MIT or Apache-2.0). Every byte belongs to exactly one block, as Kiln's live document requires.

| Block | Head | Children |
| --- | --- | --- |
| File; item | Inner attributes; attributes, docs and signature | Top-level items; members, with the closing brace as tail |
| Parameter, field, variant; table row | The whole text | None |
| Statement; arm | Text up to the first nested block; the arm's opener | Arms; statements, with the closer as tail |

Comments belong to the block that follows them, and order-insensitive lists (`use` lists, named arguments, record fields) merge as sets. Parsing is block-local: each block parses under its own production, and an error stays inside it as `ERROR` nodes. A block broken by a concurrent edit keeps its kind and position, so "the last good result for that block" is well defined.

Statement order matters only for definition before use and for the ordinals of unnamed statements. Kiln's reconcile step checks both after a merge, turning a change into `Conflict::Text` on the block (KLN).

**Decision D-ING-18:** The grammar serves structural editing: newline-terminated statements, one statement per block, comments owned by the next block, named arguments merged as sets, atomic literals, block-local parsing. *Why:* the live document needs a block per unit of concurrent work and an owner per byte, and file-level recovery re-associated blocks (R3-32). *Rejected:* a projectional editor (reviews and agents use text); semicolons with free layout (two diffs); file-level recovery. (revised in round 2)

Data modules, such as ELX's `Schematic` and `Layout`, are `table { … }` literals whose rows are atomic blocks. A row-specialized lexer skips the general tree and builds lossless nodes lazily when a row is edited. The target is 10⁶ rows parsed and hashed in under 1 s natively (ING-O-37), measured in phase 2 before ELX needs it. If missed, the module splits by board region.

**Decision D-ING-27:** Data modules stay Ingot text, with no binary sidecar. *Why:* merge, live documents, span provenance, `CallSite`s and Git export all work on text, and a second format needs a second path for each (R9-34). *Rejected:* a binary sidecar keyed by statement identity, the round 2 fallback; a data format per subsystem.

### Formatting and structural edits

`crucible fmt` produces one idempotent layout per block: 100 columns, 4-space indents, one argument or pipeline stage per line when broken, alignment only in tables. Every GUI action and agent edit becomes the smallest `SourcePatch` list the formatter leaves unchanged:

| Action | Minimal source edit |
| --- | --- |
| Change a dialog value; drag a dimension | Replace one literal token, keeping its unit; drags replace the literal UIX's edit plan chose |
| Drag a sketch entity | Rewrite the seeds that moved by more than the quantum (D-ING-26); a drag that moves nothing writes nothing |
| Edit a driving dimension on a drawing | Replace the literal it traces to by provenance, else offer ranked edit plans; driven dimensions are read-only (MEC) |
| Add a feature | Insert one statement after the anchor, binding a fresh name derived from the feature (`fillet_2`) |
| Delete or reorder a feature | Remove or move one statement block with its comments, refused if a binding would precede its definition |
| Suppress; set a tolerance | Toggle `#[suppressed]`; rewrite `4mm` to `4mm ± 0.1mm` |
| Rename a binding | Rename every use and add `#[was(old_name)]`, keeping entity names |
| Add a check | Insert a `require` statement, or attach `.require(…)` to a single-expression body |

### Language service and tools

The language service implements LSP 3.17 semantics in `ingot-service`. The UI and agents reach it through `api`, and it also runs over stdio with first-party VS Code and Zed extensions. A custom request, `crucible/reveal`, drives Crucible's viewport from those editors; the in-app code panel is UIX's.

It offers pull diagnostics with evaluation failures, semantic tokens for units and roles, hover with values and bounds, and inlay hints for dimensions and flavors. Every fix is a code action, and a source map links each `EntityId` to its creating `CallSite` and span. Targets: completion and hover within 50 ms, diagnostics for an edited 2,000-line module within 100 ms.

**Decision D-ING-25:** In phase 1 the language service ships in Crucible and over stdio with VS Code and Zed extensions, plus a viewport request. *Why:* code-CAD users already work in those editors, and an in-app editor alone would compete with them (R6-23). *Rejected:* the in-app panel as the only editor; external editors without cross-probing.

| Tool | Behavior | Phase |
| --- | --- | --- |
| Debugger | Replays a feature call in the interpreter from cached operation results, so stepping never recomputes geometry; Debug Adapter Protocol with `stepBack` and `reverseContinue`; Bodies colored by creating `CallSite` | 2 |
| REPL and notebooks | Cells compile as modules importing earlier cells; `.ingot` files with `//% cell` markers; outputs never saved | 2 |
| Tests | `#[test]`, `#[test(golden)]` comparing `ObjectId`s, `#[test(property, cases:)]` with seeded parameters; `assert_close` passes only on enclosures; failures shrink to a reproducible call | 1 |
| Benchmarks | `#[bench]` reports deterministic fuel and wall time; CI tracks fuel exactly and time statistically; `ops: cached` or `ops: cold` | 1 |

Tests are deterministic, so a flaky test is an engine defect.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Lossless tree and block-local parsing | Every byte in one block; errors stay inside it | `ERROR` nodes; never a crash | ING-O-2, ING-O-29 | 0 |
| Data modules | `table` rows as atomic blocks; row lexer; 10⁶ rows under 1 s (target) | A miss splits the module | ING-O-37 | 2 |
| Formatter and structural edits | Canonical, minimal, comment- and name-preserving; seed and drawing edits | Refused edits explain why | ING-O-10 | 1 |
| Language service | LSP 3.17 in-app and over stdio; viewport request | Degrades to plain text editing | ING-O-21 | 1 |
| Debugger | Replay from cache; reverse stepping | — | ING-O-22 | 2 |
| REPL and notebooks | Cells as modules; outputs from Kiln | — | ING-O-5 | 2 |
| Tests and benchmarks | Geometric assertions; golden and property tests; fuel tracking | Deterministic failures | ING-O-1, ING-O-33 | 1 |
| KCL importer | KCL programs to Ingot with explicit units (D-ING-19) | Unmapped constructs listed | ING-O-36 | 3 |

## State of the art

| Aspect | Zoo KCL | Onshape FeatureScript | CadQuery, build123d | OpenSCAD | Ingot |
| --- | --- | --- | --- | --- | --- |
| Typing | Numbers take the file's default unit | Dynamic, with `ValueWithUnits` | Dynamic Python | Dynamic; `undef` | Static; inferred bodies, required signatures |
| Units | "KCL doesn't support area, volume, or other higher-dimension units" | Dimensional analysis at run time | None | None | Rational dimensions, kinds, affine temperatures, at compile time |
| Tolerances | None | None in the language | None | None | `Tol<T>` with affine worst case, explicit statistics, typed GD&T |
| Entity selection | Tags (`tag = $name`); edges by adjacent faces (`sideFaces`), with an `index` fallback | `qCreatedBy(id + …)` over feature ids | String selectors (`">Z"`); build123d sorting, `Select.NEW` | No face or edge queries | Provenance and role queries, anchored ranks |
| Purity | Mostly functional | No external input, time or randomness | Python: anything | Functional; last assignment wins | Pure, fuel-bounded, explicit keyed randomness |
| UI generation | Sketches in function bodies not editable by point-and-click | Precondition annotations | None | Customizer comments beside variables | Signatures and attributes |
| Execution | Zoo's hosted engine, view streamed as video | Part Studio regeneration in Onshape | Local Python | Local | Local on every Tier 1 target and in browsers |

KCL's documentation gives `10in * 25.4` as `254in`, and FeatureScript threads `context` and `id` through every call; Ingot's types and dataflow remove both.

**Decision D-ING-19:** Crucible builds Ingot from scratch and does not fork KCL's MIT-licensed implementation, studying its tests and documentation with attribution. *Why:* most of Ingot is new, and `kcl-lib` couples execution to an engine connection that cloning its `ExecutorContext` shares. *Rejected:* forking `kcl-lib` (replaced anyway, with default units); KCL source compatibility (conflicts with principle 5). A KCL importer is phase 3 work in `io/`.

Figures are targets on contract section 13.3's reference laptop.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Units and dimensions | Units-of-measure inference (F#); kinds and affine points (mp-units, after ISO 80000) | F# units of measure; mp-units; Pint | Rational dimensions, kinds, strong angular system, erased at run time | ING-O-4; check time under 5% of front-end time |
| Tolerance arithmetic | Affine arithmetic (Comba and Stolfi; de Figueiredo and Stolfi); GUM and Supplement 1 | Sigmetrix CETOL 6σ (3D tolerance analysis in CAD) | Affine forms per site and realizing Part; exact coverage; name-free order | ING-O-7 |
| Approximate comparisons | Interval enclosures with three-valued logic | FLX's budgets | One decision rule over `ErrorBudget`s with conditional passes | ING-O-8 |
| Entity naming | Provenance with history (`Select.NEW`; `qCreatedBy`) | Onshape FeatureScript | Text-derived `CallSite`s, keyed iteration, anchored queries | ING-O-25, ING-O-26, ANV-O-NAME-2 |
| Incremental compilation | Red-green memoization with early cutoff (Salsa) | rust-analyzer | Salsa-style stages inside Kiln; split node outputs | ING-O-13; re-check under 30 ms |
| Execution | Compiled code "an order of magnitude faster than interpretation" (Xu and Kjolstad); Cranelift within about 14% of LLVM; browsers 45% to 55% slower than native on SPEC (Jangda and colleagues) | V8, Wasmtime; wasmi with fuel | Interpreter now; Wasm code generator when justified | ING-O-33 |
| Memory in pure languages | Perceus reference counting with reuse (PLDI 2021) | Koka | Reference counting with in-place update; Perceus in the code generator | ING-O-34 |
| Deterministic execution | Wasm with fuel and canonical semantics (Wasmtime; Wasm 3.0 deterministic profile) | Wasmtime with NaN canonicalization | One canonical interpreter; verified modules | ING-O-1 |
| Live programming | Typed holes with evaluation around them (Hazel) | Hazel | Holes from the error-resilient parser | ING-O-15 |
| Bidirectional editing | Program repair from output edits (Sketch-n-Sketch) | Sketch-n-Sketch; Onshape dimension editing | Provenance ranking, then derivatives | UIX's intent-match rate |
| Lossless syntax trees | Red-green trees (Swift libsyntax, rust-analyzer) | rust-analyzer with `rowan` | `rowan`, block grammar, block-local parsing for Loro's movable tree | ING-O-2, ING-O-29, ING-O-37; 2,000 lines reparsed under 5 ms |
| Version resolution | PubGrub | uv | PubGrub through ECO's resolver | ING-O-18 |
| Language evolution | Editions with automated migration (Rust) | Cargo | Editions plus an IIR-equality check | ING-O-19 |
| Dialogs from code | FeatureScript preconditions | Onshape | Typed signatures plus attributes | ING-O-20 |
| Sketch language | Constraint graphs catalogued by SketchGraphs | Onshape's sketcher, SketchGraphs' source | Builder blocks of symbolic entities and `Equation` items | ING-O-23 |
| Debugging | DAP with `stepBack` and `reverseContinue` | rr (record, replay, reverse execution) | Replay from Kiln's cache, exact because evaluation is pure | ING-O-22 |

## Platform notes

| Platform | Note |
| --- | --- |
| Every target | One canonical-class interpreter, so a divergence is a platform defect that ING-O-1 finds |
| Browsers | The wasm32 interpreter runs in the engine worker and yields at Kiln calls in single-threaded builds; large evaluations follow PLT's browser memory table |
| iPadOS (Tier 2) | No JIT needed: the interpreter runs in the web build inside WebKit (contract section 7.4) |
| Tier 1 preview targets | Same build; ING-O-1 and the golden products run headless |
| Code generator | Core Wasm with 128-bit SIMD only; pages allow `'wasm-unsafe-eval'`, without which "WebAssembly is blocked" (MDN) |
| Floating point | Correctly rounded operations and `detmath`; no FMA, flush-to-zero or excess precision |
| Air-gapped installs | Compiler and interpreter ship in every build; no network is needed |
| Accessibility | Diagnostics are plain text with spans |
| Tier 3 | Results stay out of shared caches until the determinism suite passes |

## Interfaces with other subsystems

### Ingot provides

| To | Provides | Types |
| --- | --- | --- |
| KLN | Front-end stages with separate IIR and diagnostics; code hashes; split outputs; program order; overrides as input cells; limits in keys; `CheckId`s and the gate predicate; block grammar and statement order; span integrity; variant regions and Instance sets; cached `Undecided` values | `CallSite`, `CheckId`, `Check` |
| ANV | `CallSite`s; `QueryPlan`s with anchored ranks and extent-use acceptances; kinded role filters; sketch helpers' sub-entities; program order for copy relabelling; `InputSensitivity`; the `Truth` rule for filters | `Query`, `Tol<T>` |
| FLX | Product- and parameter-domain `Field` syntax; `Complex<Q>`, `.absolute()`, `select`; `Expr<T, Out>`; `Approx`, `Truth` and the decision rule; `goals:`, `wrt:` and `away_from` sets | `Field<D, V>`, `Expr<T>`, `Approx<T>` |
| MEC | Features, builder blocks, symbolic constraints, inline seeds, families, `Tol<T>` with fits, forwarding and name-free order, typed aspects, keyed iteration, Instance sets, `#[configuration]` | `Feature`, `Tol<T>`, `InstanceSet` |
| ELX | `network { … }` with set-like accumulation; port power checks; `Tol` correlation groups; `CatalogSelection`; `#[configuration]`; `#[interface]`; data modules as `table` rows | `Tol<T>`, `Network` |
| COV | Records, `Range` as interval, kinds for regime functions, `require`, conditional `Pass`, the decision rule over basis enclosures | `Quantity<D>`, `Check` |
| MFG | Records, enums, `Map`, kinds for Field domains, `Decimal` and `Money<C>` with `round_minor`, `require` | `Quantity<D>`, `Check` |
| UIX | Language service; `EntityId`-to-span map; dialog metadata; overrides that follow `#[was]`; edit-plan ranking; minimal `SourcePatch`es, drawing dimensions included | `SourceSpan`, `Feature` |
| AGT | Diagnostics with `SourcePatch` fixes; the formatter; metadata and doc comments for tool schemas; `ExternalText`; span integrity; `CheckOutcome`s, the decision rule and the gate predicate | `Check`, `Feature` |
| ECO | Manifest language keys; lockfile `[language]`; editions; semantic-version rules; binding, wrapper and guest SDK conventions | `Feature` |
| PLT | The interpreter on every target; generated modules for verification from phase 2 at the earliest | `PlatformClass` |

### Ingot requires

| From | Requirement |
| --- | --- |
| KLN | Suspending scheduler; keys with `CallSite`, code hashes, limits and overrides; overridden results kept local; split outputs; Aborts and limit outcomes; `Pending` reporting; `Differentiable`; span integrity in labels; policy allowances and Waiver records; statement-order reconcile |
| ANV | Operations catalog with tangent rules; `anvil::resolve` with `NearTie`, `Partial`, `Merged` and `FragileAnchor` notes and compiling fixes; sampled stability analysis (`RankSwap`); face, edge and vertex roles with surface or extent use; copy relabelling; equal decisions at every fidelity; certified sketch solves; canonical geometric order; `shape_velocity` from phase 2 |
| FLX | Operations catalog; forms and `solve`; regularized reductions with `ErrorBudget`s; calibrated bounds with class envelopes and refinement confirmation; singular sets with default distances; tangent and adjoint rules; `away_from` over several sets; basis enclosures as input parts |
| COV | `std::physics` and `std::materials`; property reads as basis enclosures (D-COV-13) |
| ELX | `network { … }` semantics; `Schematic` and `Layout` data modules and a layout fixture for ING-O-37; `CatalogSelection` over pinned definitions and offers |
| PLT | `detmath` and `det_sum`; Wasm executors, the determinizer and module verification; the `Interactive` pool lane; text normalization; the browser memory table |
| ECO | Registry, signing, interface diff, Wasm component bundles, `crucible:` WIT packages, `parts::` packages, RFCs for std kinds |
| MEC | GD&T records and validators per dialect, with zone mathematics for Y14.5-2018-only constructs; `pmi_target_resolved`; `general_tolerance`; roles and keyed generators in std features; `std::mech::refgeom`; `std::standards::iso286` from ISO 286-1's formulas; `default_distribution`; the zone and rebuild variation paths; `fasten` returning an Instance set; Part and Assembly name-free encodings |
| AGT | `SourcePatch` application; `ExternalText` handles for untrusted spans and evaluated strings; `evaluate.subscribe` and `edit.stream` |

## Oracles

All oracles live under `oracles/ingot/` (protected). The corpus is std, the golden products, every registry package's tests and a generated set of random well-typed programs.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| ING-O-1 | Conformance of the interpreter on every Tier 1 target and browser engine, and of compiled code, on values, failures, fuel and Kiln call sequences; IIR across compiler releases; `sum` against `det_sum` | Bit-identical on the corpus |
| ING-O-2 | Parse then print, for valid and invalid inputs | Every byte reproduced |
| ING-O-3 | Parser fuzzing on arbitrary bytes | No crash, hang or unbounded memory in 10⁹ executions per release |
| ING-O-4 | Units: seeded dimension, kind, affine, degree-radian, rpm-hertz and hertz-phase errors, plus each RFC kind's error; at least 50 textbook rotational, electrical and thermal formulas | Every error rejected with its code or lint; every formula type-checks without casts |
| ING-O-5 | Typing judgments on a curated corpus; random well-typed programs; `Decimal` rounding | Expected judgments; zero internal type failures; round half to even on every product and quotient |
| ING-O-6 | Deepest legal recursion on every target, and one deeper | Runs everywhere; fails with `ING6302` everywhere |
| ING-O-7 | Tolerances against exact rational stacks and 10⁶ samples per nonlinear case; Part-keyed symbols; coverage against exact convolution; a 10⁵-site stack; statistics under re-randomized names | Exact linear stacks; containment otherwise; spacers vary independently; `.rss` within `.limits()`; identical bits after renaming |
| ING-O-8 | Comparisons with injected bounds, kinds, envelopes, refinements and confidences; one property read feeding two checks of opposite sign | Never `True` or `False` against the exact relation; `Indicator` and unquantified parts never decide; `conditional_on` exact; both checks conservative |
| ING-O-9 | Machine-applicable fixes in the corpus | 100% compile and remove their diagnostic |
| ING-O-10 | Recorded GUI sessions, sketch drags included | Minimal patches; comments and untouched `CallSite`s kept; a drag that moves nothing writes nothing; rounded seeds rebuild bit-identically |
| ING-O-11 | Query lowering and roles | Equal queries hash equal; unanchored ranks raise `ING-L-FragileSelector`; `Tol` filters fail; every role of every std sweeping feature resolves; a wrong-kind role fails with `ING5002` |
| ING-O-12 | Drag specialization and overrides on golden-product drag scripts | Residual and full programs bit-identical; an overridden result never answers a request without the override |
| ING-O-13 | Minimal re-evaluation over 500 scripted edits (shared with KLN-O-MIN-1) | Re-executed nodes equal the reference set; none after fuel-only edits |
| ING-O-14 | Differential fuzzing of the code generator: interpreter against compiled code, optimized against unoptimized | No divergence per release |
| ING-O-15 | Programs with random holes | Hole-independent bindings equal the complete program's |
| ING-O-16 | Derivatives on smooth programs; dependence sets; phase 1 ranking on drag scripts | Taylor order 2 ± 0.1; dependence exact; provenance literal ranked first |
| ING-O-17 | `#[ingot::feature]`, bindings and the guest SDK | Checked-in WIT and wrappers match regenerated ones; `ingot_sdk` matches the WIT imports; units match WIT aliases |
| ING-O-18 | Unsatisfiable dependency fixtures; two-major coexistence | Every failure explained; no silent choice |
| ING-O-19 | Edition migrations on the corpus | IIR and output hashes preserved |
| ING-O-20 | Metadata and examples | Every std feature has a dialog, docs and an evaluated example; this tab's examples evaluate |
| ING-O-21 | Service latency on an edit-replay corpus, in-app and over stdio | Within the stated targets at p95 |
| ING-O-22 | Debugger replay | Forward then backward steps give identical frames |
| ING-O-23 | A fixed SketchGraphs sample converted to sketch blocks | Every constraint type expressible; at least 99% re-solve within tolerance (target) |
| ING-O-24 | `f(n) = f(n + 1)` on every Tier 1 target | Aborts with `DemandDepthExhausted`; no memo entry |
| ING-O-25 | Golden products through Git export and re-import; appended, wrapped and inserted calls of other names; a prepended same-name call; renames with `#[was]` | Untouched `CallSite`s and `EntityId`s unchanged; the prepend raises `ING-L-RepeatedStage`, whose fix keeps later names |
| ING-O-26 | One element inserted into or removed from geometry-driven patterns and query loops | Only that element's entities renamed |
| ING-O-27 | Adding or removing any `require`; editing a check's limit | Every non-check node key unchanged; the edited check keeps its `CheckId` and Evidence records |
| ING-O-28 | Evaluations under varied organization ceilings | One limit outcome per source and manifest; a lower ceiling aborts at admission |
| ING-O-29 | Block-local parsing | Concatenated blocks reproduce the tree; a failing block keeps its kind and position |
| ING-O-30 | Variant regions and Instance sets | Computed conditions rejected with `ING2601`; the 150% BOM equals enumeration on small fixtures; a new hole changes a quantity, not the BOM structure |
| ING-O-31 | Contract section 6's example | Compiles; its check decides at `SignOff`, never `Undecided { SingularPoint }`; `width + load` gives `ING3001` |
| ING-O-32 | Free-text spans on a labelled corpus; hidden characters; strings evaluated from untrusted spans | Classification matches; hidden characters fail with `ING0003`; evaluated strings keep their span's integrity |
| ING-O-33 | Interpreter speed | Within the stated targets; Ingot's rebuild share reported |
| ING-O-34 | 500 concurrently suspended golden-product feature calls in a browser engine worker | Within the stated memory target |
| ING-O-35 | Branches and `where:` filters on `Undecided`, under an `Interactive` ceiling, then a `SignOff` ceiling with warm caches | The second shows `Pending`, then the decided value; `ING6401` and `ResolveError::Ambiguous` appear only in reports at the ceiling |
| ING-O-36 | KCL sample programs through the importer | Each builds the reference geometry or lists unmapped constructs |
| ING-O-37 | Data-module parsing on an ELX layout fixture of 10⁶ rows | Parsed and hashed in under 1 s natively (target); lossless round trip of edited rows |
| ING-O-38 | The gate predicate over generated outcomes, allowances and Waiver records | Matches contract section 5; `Warning` failures never block; an uncovered conditional `Pass` blocks; `#[waive]` alone counts nowhere |

## Phasing

| Phase | Ingot contribution to the gate |
| --- | --- |
| 0 | "Unit errors fail to compile" is ING-O-4; the interpreter and Kiln protocol join the determinism suite (ING-O-1, ING-O-6); parser, types, interpreter and `CallSite`s (ING-O-25) in milestone 1 of contract section 13.2 |
| 1 | GP1 and GP2 build from std Ingot on the interpreter: forwarded tolerances, `Approx`, the decision rule, checks and the gate predicate, queries, sketches, GD&T, families, variant regions, packages, dialogs, the language service, tests; interpreter targets met (ING-O-33). The code generator and Perceus are deferred (contract section 13.2) |
| 2 | GP3 and GP4: Instance sets for fasteners, catalog selections, variants at scale; the data-module target measured (ING-O-37); the code generator if Ingot exceeds 2% (ING-O-14); debugger and notebooks; reverse-mode derivatives; the first edition migration |
| 3 | GP5: ELX data modules and `network { … }` at scale; KCL importer (ING-O-36) |
| 4 | GP6: large symbolic forms and parameter-domain forms in use (FLX) |
| 5 and later | Proposed: a mechanized soundness proof of the dimension and tolerance calculus, and a second interpreter for aerospace and medical certification |

Ingot's types for shared physics capabilities arrive early, but each capability takes its phase from contract section 13.4: DFN cells, for example, are phase 5.

## Open questions

This revision decides all nine round 2 questions:

| Question | Decided by |
| --- | --- |
| Kind granularity; frequency into phase | The RFC rule; `ING-L-HertzPhase` |
| Geometry-driven Instances | Instance sets (D-ING-22) |
| Affine arithmetic at scale | Condensation above 4,096 symbols |
| ELX data modules | No sidecar (D-ING-27) |
| `Decimal` resolution | 10⁻⁹, round half to even, `round_minor` |
| Feature granularity | `ING-L-FeatureKind` |
| Jacobian types | Entry-level `Mat` diagnostics |
| Literal sites under live edits | Overrides follow `#[was]` |

Findings declined or applied in part:

- R2-06: calls get no CRDT identity, because contract section 5 derives call identity from name and occurrence; R9-36's lint closes the gap.
- R3-33: one instance per worker with state machines applies to the code generator; the interpreter isolates calls with heap frames.
- R6-33: ING sets only its own ratios; Wasm component and user-form ratios belong to PLT, ECO and FLX.
- R3-47: Ingot runs on the interpreter on iPadOS, so the Pulley fallback concerns Wasm components only.
- R2-18: ING adds the dialect modules; the extended GD&T record is MEC's.
- R7-02: contract section 17 declines the near-maximal-set rule, because estimates are least reliable next to a singular set.
- R8-08 and R9-17: merged into one name-free key, led by R8-08's sensitivity order so Sobol's first dimensions go to the largest contributors.
- R8-20 and R9-16: merged into `instances(of:, at:, min:)`.
- R8-51 and R9-49: their condensation rules conflict; ING keeps R8-51's mechanism with R9-49's 4,096-symbol threshold, bounding memory.
- R9-18: applied in another form. Releases emit bit-identical IIR, so no second key is needed and code hashes never depend on which release ran first.

## Contract change requests

None in round 3. Earlier requests:

- CCR-ING-11, pending branches: accepted in contract v5 and refined in v6 (R9-02); contract section 5 (`Truth`).
- CCR-ING-12, rotation and phase: accepted in contract v5; contract section 5 (`Quantity<D>`).
- CCR-ING-13, the call-site frame path: accepted in contract v5, renamed `CallSite` in v6; contract section 5 (`CallSite`).

## Sources

1. Zoo, "KCL Language Reference" (index): https://zoo.dev/docs/kcl-lang
2. Zoo, "Numeric types and units": https://zoo.dev/docs/kcl-lang/numeric
3. Zoo, "Pipelines": https://zoo.dev/docs/kcl-lang/pipelines
4. Zoo, "Functions": https://zoo.dev/docs/kcl-lang/functions and https://raw.githubusercontent.com/KittyCAD/modeling-app/main/docs/kcl-lang/functions.md
5. Zoo, "Projects and modules": https://zoo.dev/docs/kcl-lang/modules
6. Zoo, KCL settings: https://raw.githubusercontent.com/KittyCAD/modeling-app/main/docs/kcl-lang/settings.md
7. KittyCAD, modeling-app repository: https://github.com/KittyCAD/modeling-app ; license: https://raw.githubusercontent.com/KittyCAD/modeling-app/main/LICENSE ; kcl-lib README: https://github.com/KittyCAD/modeling-app/blob/main/rust/kcl-lib/README.md
8. kcl-lib API documentation: https://docs.rs/kcl-lib/latest/kcl_lib/
9. Onshape, "Introduction to FeatureScript": https://cad.onshape.com/FsDoc/intro.html
10. Onshape, FeatureScript UI specification: https://cad.onshape.com/FsDoc/uispec.html
11. Onshape, FeatureScript standard library: https://cad.onshape.com/FsDoc/library.html
12. Onshape, FeatureScript variables and value semantics: https://cad.onshape.com/FsDoc/variables.html
13. CadQuery introduction: https://cadquery.readthedocs.io/en/latest/intro.html
14. build123d, builder concepts: https://build123d.readthedocs.io/en/latest/key_concepts_builder.html
15. build123d, topology selection: https://build123d.readthedocs.io/en/latest/topology_selection.html
16. OpenSCAD User Manual, General: https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/General ; repository: https://github.com/openscad/openscad
17. mp-units, the affine space: https://mpusz.github.io/mp-units/latest/users_guide/framework_basics/the_affine_space/
18. mp-units, systems of quantities: https://mpusz.github.io/mp-units/latest/users_guide/framework_basics/systems_of_quantities/
19. mp-units, strong angular system: https://mpusz.github.io/mp-units/latest/users_guide/systems/strong_angular_system/
20. Pint, non-multiplicative units: https://pint.readthedocs.io/en/stable/user/nonmult.html
21. Microsoft, F# units of measure: https://learn.microsoft.com/en-us/dotnet/fsharp/language-reference/units-of-measure
22. BIPM, JCGM publications (GUM, Supplements 1 and 2): https://www.bipm.org/en/committees/jc/jcgm/publications
23. Wikipedia, "Affine arithmetic" (for Comba and Stolfi 1993; de Figueiredo and Stolfi 2004): https://en.wikipedia.org/wiki/Affine_arithmetic
24. ASME, Y14.5 Dimensioning and Tolerancing: https://www.asme.org/codes-standards/find-codes-standards/y14-5-dimensioning-tolerancing
25. ASME, Y14.5.1-2019: https://www.asme.org/codes-standards/find-codes-standards/y14-5-1m-mathematical-definition-dimensioning-tolerancing-principles/2019 ; https://www.asme.org/codes-standards/find-codes-standards/y14-5-1-mathematical-definition-dimensioning-tolerancing-principles
26. ISO 1101:2017: https://www.iso.org/standard/66777.html
27. ISO 5459:2024: https://www.iso.org/standard/87855.html
28. ISO 14405-1:2016 (withdrawn): https://www.iso.org/standard/65202.html ; ISO 14405-1:2025: https://www.iso.org/standard/80703.html
29. ISO 286-1:2010: https://www.iso.org/standard/45975.html
30. ISO 22081:2021: https://www.iso.org/standard/72514.html
31. ISO 8015:2011: https://www.iso.org/standard/55979.html
32. Cranelift README: https://github.com/bytecodealliance/wasmtime/blob/main/cranelift/README.md
33. Jangda, Powers, Berger and Guha, "Not So Fast: Analyzing the Performance of WebAssembly vs. Native Code", USENIX ATC 2019: https://www.usenix.org/conference/atc19/presentation/jangda
34. Xu and Kjolstad, "Copy-and-Patch Compilation": https://arxiv.org/abs/2011.13127
35. Wasmtime, deterministic execution: https://docs.wasmtime.dev/examples-deterministic-wasm-execution.html
36. Wasmtime, platform support: https://docs.wasmtime.dev/stability-platform-support.html ; tiers: https://docs.wasmtime.dev/stability-tiers.html
37. WebAssembly 3.0 specification, profiles appendix: https://webassembly.github.io/spec/core/appendix/profiles.html
38. Component Model, WIT reference: https://component-model.bytecodealliance.org/design/wit.html
39. wit-bindgen: https://github.com/bytecodealliance/wit-bindgen
40. jco: https://github.com/bytecodealliance/jco
41. wasm-instrument: https://github.com/paritytech/wasm-instrument
42. wasmi: https://github.com/wasmi-labs/wasmi
43. Reinking, Xie, de Moura and Leijen, "Perceus: Garbage Free Reference Counting with Reuse" (PLDI 2021, extended version): https://www.microsoft.com/en-us/research/publication/perceus-garbage-free-reference-counting-with-reuse/
44. CORE-MATH project: https://core-math.gitlabpages.inria.fr/
45. Salmon, Moraes, Dror and Shaw, "Parallel Random Numbers: As Easy as 1, 2, 3" (SC11): https://www.thesalmons.org/john/random123/papers/random123sc11.pdf
46. Reissmann, Meyer, Bahmann and Själander, "RVSDG: An Intermediate Representation for Optimizing Compilers": https://arxiv.org/abs/1912.05036
47. Omar, Voysey, Chugh and Hammer, "Live Functional Programming with Typed Holes": https://arxiv.org/abs/1805.00155
48. Chugh, Hempel, Spradlin and Albers, "Programmatic and Direct Manipulation, Together at Last": https://arxiv.org/abs/1507.02988
49. Seff, Ovadia, Zhou and Adams, "SketchGraphs": https://arxiv.org/abs/2007.08506
50. Kleppmann, Mulligan, Gomes and Beresford, "A highly-available move operation for replicated trees": https://martin.kleppmann.com/papers/move-op.pdf
51. Loro, tree tutorial: https://loro.dev/docs/tutorial/tree
52. rowan: https://github.com/rust-analyzer/rowan ; rust-analyzer syntax documentation: https://github.com/rust-lang/rust-analyzer/blob/master/docs/book/src/contributing/syntax.md
53. Salsa overview: https://salsa-rs.github.io/salsa/overview.html
54. PubGrub guide: https://pubgrub-rs-guide.pages.dev/ ; pubgrub-rs: https://github.com/pubgrub-rs/pubgrub
55. The Rust Edition Guide: https://doc.rust-lang.org/edition-guide/editions/index.html
56. Language Server Protocol 3.17: https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/
57. Debug Adapter Protocol overview and specification: https://microsoft.github.io/debug-adapter-protocol/overview ; https://microsoft.github.io/debug-adapter-protocol/specification
58. Swift Evolution SE-0289, result builders: https://github.com/swiftlang/swift-evolution/blob/main/proposals/0289-result-builders.md
59. MDN, `script-src` and `'wasm-unsafe-eval'`: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/script-src
60. Unicode Standard Annex #31, "Unicode Identifiers and Syntax": https://www.unicode.org/reports/tr31/
61. Ryū, shortest round-tripping floating-point output: https://github.com/ulfjack/ryu
62. OCaml manual, extensible variant types: https://ocaml.org/manual/5.2/extensiblevariants.html
63. Zoo, "Edge references": https://zoo.dev/docs/kcl-lang/edge-references
64. OpenSCAD User Manual, Customizer: https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Customizer
65. OpenSCAD cheat sheet: https://openscad.org/cheatsheet/
66. SketchGraphs repository: https://github.com/PrincetonLIPS/SketchGraphs
67. rr, record and replay debugger: https://rr-project.org/
68. Sigmetrix, CETOL 6σ: https://www.sigmetrix.com/software/cetol
69. CADforum, shaft and hole tolerances by ISO 286-2: https://www.cadforum.cz/en/tolerance.asp
70. SIX, ISO 4217 currency code list one: https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xml
