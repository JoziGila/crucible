# Ingot language (ING)

Ingot is Crucible's design language: pure, strict and statically typed, with units, tolerances, approximation error and geometric references as types. A canonical-class interpreter runs it on every target, and each operation call becomes a Kiln node named from source text alone. The visual editor, the code editor and agents edit one lossless syntax tree, so every edit is a minimal, mergeable source change.

## Scope and principles

| ING owns | Others own |
| --- | --- |
| Syntax, grammar, formatting, editions | Operation semantics and behavior versions (ANV, FLX) |
| Types: `Quantity<D>`, `Tol<T>`, `Approx<T>`, `Truth`, `Expr<T>`, records, enums, traits | `ErrorBound`, `ErrorBudget` and `CheckOutcome` layouts in `base`; `Field` (FLX) |
| `OpSite`; query syntax and lowering; the decision rule for `Truth` and checks | `EntityId`, lineage and `anvil::resolve` (ANV) |
| Evaluation semantics, `Failure` and `Abort` in the language, per-call limits | Scheduling, caching, labels, evaluation-wide limits and the determinism policy (KLN); mechanisms (PLT) |
| The interpreter, the Ingot IR and the deferred code generator | The kernel IR (FLX, `kernels`); the determinizer (PLT) |
| Diagnostics, fixes and check semantics | Release policy (`repo`); the verifier and `api` (AGT) |
| Modules, manifest language keys, lockfile `[language]`, semantic-version rules | Registry and signing (ECO); lockfile storage and merge (KLN) |
| `#[ingot::feature]` and WIT bindings | WIT worlds and capabilities (ECO) |
| Feature metadata, language service, debugger, tests | Dialog rendering, code panel and viewport (UIX); agent tools (AGT) |

| Crate (contract section 12) | Contents | Phase |
| --- | --- | --- |
| `ingot-syntax` | Lexer, block-local parser, lossless tree, formatter, edition migrations | 0 |
| `ingot-types` | Name resolution, inference, dimension and tolerance algebra, traits, diagnostics catalog | 0 |
| `ingot-ir` | Ingot IR (IIR), lowering, `OpSite` derivation, the reference interpreter, differentiation | 0 |
| `ingot-bindgen`, `ingot-macros` | WIT bindings and `#[ingot::feature]` | 1 |
| `ingot-service` | Language server, structural edits, test runner; debugger and notebooks | 1; 2 |
| `ingot-codegen` | IIR to WebAssembly, entering only when justified ("Execution") | 2 at the earliest |

Every Ingot crate is `forbid(unsafe_code)`.

1. **Pure.** No expression observes time, randomness, files, network, thread order, memory addresses or entity names. Randomness is an explicit keyed value.
2. **Strict and bounded.** Call by value, left to right. Every node ends in a value or a typed `Failure`; every Evaluation ends or aborts.
3. **Physics in types.** Dimensions, affine quantities, tolerances and approximation error are types.
4. **Geometry by provenance, names from text.** Code never holds an entity index, and call-site identities come from source text only.
5. **One program, three editors.** Every GUI action and agent edit is a minimal edit of the lossless tree.
6. **No privileged code.** std is ordinary Ingot; operations and Wasm components are reached through `extern` declarations anyone can write.
7. **Errors are values with fixes; the environment is never a value.** A `Failure` has a code, a reason, a location and typed fixes. An `Abort` is not a value.
8. **No macros.** Builder blocks, attributes and generics cover what macros would; code generation happens only outside the language.

**Decision D-ING-1:** Ingot is a pure, strict, expression-oriented language with immutable values, full type inference inside bodies, and required type signatures on every named function, feature and record. *Why:* signatures let each module type-check alone, bounding recompilation to it and its dependents, and they generate dialogs and documentation. *Rejected:* whole-program inference (errors appear far from causes); dynamic typing as in CadQuery and OpenSCAD (unit errors surface late or never); mutable variables (they break the dataflow lowering); lazy evaluation (costs and failures would depend on demand order, and Kiln is already demand-driven).

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
    let web = base.face(role: end_cap).edge(role: side(outline.top)) |> rib(height: 20mm, t: thickness)
    let body = base + web
    let solid = body |> fillet(body.edges(new), 2mm)
    let p = part(solid, name: "Bracket").material(alu_6061_t6)
    let clamp = base.face(role: start_cap)
    let study = static_stress(p, fixed: clamp, force: load, on: web.face(role: end_cap))
    let stress = study.von_mises.max(over: p.away_from(clamp, 2 * thickness))
    p.require(stress < 0.6 * p.material.yield_strength(at: 20degC))
}
// width + load  →  error ING3001: cannot add Length and Force
```

`thickness` arrives as a `Tol<Length>`: the body computes with the nominal, and `extrude` attaches the tolerance as PMI (D-ING-4). The web's edge is chosen by the role of the rectangle's `top` edge, never by rank. `stress` is an `Approx<Stress>` over a region away from the clamp (FLX), so the check is three-valued (D-ING-7).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Canonical example | Contract section 6 compiles and evaluates with the outcome kinds stated there | Any other diagnostic or outcome fails the oracle | ING-O-31 | 1 |
| Purity | No expression observes time, randomness, files, network, thread order, addresses or names | Not expressible | ING-O-1 | 0 |

## Lexical syntax and grammar

### Source text

| Aspect | Rule |
| --- | --- |
| Encoding | UTF-8 in NFC, normalized by the platform layer on load; non-NFC input that bypassed it fails with `ING0002` |
| Hidden characters | Bidirectional controls, zero-width characters and Unicode tag characters are rejected anywhere in source (`ING0003`); string literals write them as escapes such as `\u{200B}` |
| Line endings | LF; CRLF is accepted and normalized by the formatter |
| Identifiers | Letters, digits and `_`, not starting with a digit; Unicode letters follow UAX #31 default identifiers [unverified: UAX #31 not opened]; `ING-L-MixedScript` flags mixed scripts |
| Case | `snake_case` for functions, features, variables, fields and modules; `PascalCase` for types, traits and enum variants; deny-by-default lint `ING-L-Naming` |
| Statements | A newline ends a statement unless inside brackets, after a binary operator, `,` or `\|>`, or before a line starting with `.`, `\|>`, `else`, `and`, `or` or `±`. No semicolons |
| Comments | `//` and nesting `/* … */`; `///` documents the next item and `//!` the module, both CommonMark |
| Attributes | `#[name(args)]` on the next item, parameter, field or statement; `#![name(args)]` on the module |

Keywords: `and`, `as`, `else`, `enum`, `extern`, `false`, `feature`, `fn`, `for`, `if`, `impl`, `in`, `let`, `match`, `not`, `or`, `pub`, `record`, `require`, `self`, `Self`, `trait`, `true`, `try`, `type`, `use`, `where`. Contextual keywords: `kind` at item position, `table` before `{`, `package` and `super` in paths. There is no `while` and no `return`; `%` is the percent suffix, so remainders are the functions `rem` and `mod`.

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

The unit table is closed per edition. It holds SI units with SI prefixes, the radian, accepted non-SI units (`min`, `h`, `L`, `t`, `bar`, `eV`, `deg`, `rev`, `arcmin`, `degC`, `degF`, `degR`), US customary units (`in`, `ft`, `thou`, `lb`, `lbf`, `psi`) and D-ING-3's rotational units. Prefixes compose only where defined, so `ft` is never a femtotonne.

Packages cannot add units; the knot is a constant, `std::units::knot`. Canonical spellings are ASCII (`um`, `deg`, `degC`, `ohm`); the formatter rewrites `µm`, `°`, `Ω` and `+-`, and `±` is the one non-ASCII token.

**Decision D-ING-2:** Every dimensional literal carries its unit, no file or package declares a default unit, and the compiler converts a literal to its SI value by exact rational arithmetic with one correct rounding. *Why:* a default unit makes a bare number mean different things in different files (KCL's documentation calls such a number "possibly any of them"), and exact conversion makes `25.4mm == 1in` hold bit for bit everywhere. *Rejected:* KCL's `defaultLengthUnit` (meaning depends on file context); multiplying by a floating-point factor (double rounding makes equal lengths unequal); a unitless zero accepted as any quantity (`0mm` is explicit).

### Grammar

The grammar is LL(1) after the lexer, except that `{` after an expression needs a second token to separate record literals, blocks and builder blocks. Builder blocks follow only a call's closing parenthesis, and one ending an `if`, `match` or `for` head needs parentheses, as a record literal does.

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

Named arguments may appear anywhere; positional arguments fill the remaining parameters in order, and `ING-L-NameArguments` asks for names after the second positional argument. Within one block each `let` name is unique (`ING1102`), so every statement has a stable textual name; inner blocks may shadow outer names. There is no ad hoc overloading: one name has one signature.

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
| `Real` | Finite binary64, exactly `Quantity<1>`; an operation that would produce NaN or an infinity fails with `ING6102` at that expression |
| `Quantity<D>` | A `Real` in coherent SI units with dimension `D`; checked at compile time, erased at run time |
| `Temperature` | An absolute temperature, affine ("Affine quantities") |
| `Complex<Q>` | Pairs of one dimension; the imaginary unit is `im` |
| `Decimal` | Exact decimals at 10⁻⁹ in a 128-bit integer, for `Money<C>` and counted data; a literal adopts it exactly or fails (`ING2003`) |
| `String`, `ExternalText` | Immutable NFC text; untrusted text from outside the design, written `external("…")` with its origin and never implicitly a `String` (AGT) |
| `Tol<T>`, `Approx<T>`, `Truth`, `Expr<T>` | Tolerances, approximations, three-valued results, staged symbolic values |
| `Body`, `Part`, `Assembly`, `Instance`, `Field<D, V>`, `Material` | Handles to values Kiln holds ("Geometry in the language") |
| `Query<K>`, `Entity<K>` | Selections and resolved entities of kind `Face`, `Edge`, `Vertex`, `Region`, `Point` or `ShapeAspect` |
| `Point3`, `Vec3<D>`, `Direction`, `Transform`, `Plane`, `Axis`, `CoordSys` | Geometric values; `Point3` is affine over `Length` |
| `Seed`, `Rng` | Explicit randomness ("Evaluation") |

`width / 2mm` is a `Real`, so every dimensionless ratio is one type. `Int` multiplies quantities directly (`i * 6mm`); an `Int` above 2⁵³ in magnitude fails that conversion with `ING6103` rather than rounding.

### Dimensions

A dimension is a vector of rational exponents over eight base dimensions: the seven SI base dimensions plus plane angle `A`. Solid angle is `A²`. Exponents are rational because engineering needs them: fracture toughness is `MPa*m^(1/2)` and noise density `V/Hz^(1/2)`.

```
kind Length = L                              // std prelude: named dimensions
kind Stress = M / (L * T^2)
kind Torque: M * L^2 / (T^2 * A)             // a kind: J/rad
kind Energy: M * L^2 / T^2
kind AngularFrequency: 1 / T                 // oscillation rate; not an angle per time
type Velocity = Quantity<L / T>
```

`kind X = D` names a dimension, and `kind X: D` declares an ISO 80000 quantity kind, which never adds to or compares with another kind of its dimension. Results are unkinded until they meet an annotation, and mixing kinds fails with `ING3002`, which offers an `as` cast. std declares kinds only where confusion causes real errors, such as frequency against angular frequency or activity (mp-units notes that hertz, becquerel and baud share `T⁻¹`).

| Expression | Rule |
| --- | --- |
| `a + b`, `a - b`, comparisons, `min`, `max` | Same dimension and compatible kind |
| `a * b`, `a / b` | Exponents add or subtract; `Int / Int` is a `Real`; `div`, `rem` and `mod` are integer operations |
| `a ^ n` | `n` is a compile-time rational unless `a` is dimensionless |
| `sqrt`, `cbrt` | Exponents halve or divide by three |
| `sin`, `cos`, `tan` | Take an `Angle` or a dimensionless phase; return `Real` |
| `asin`, `acos`, `atan`, `atan2(y, x)` | Return `Angle` |
| `exp`, `ln`, `log10` | Take and return `Real`; `ln(p / p0)` is the idiom |

Rotational kinds follow the strong angular system of contract section 5: `Torque` is J/rad, `MomentOfInertia` kg·m²/rad², `RotationalStiffness` J/rad² and `AngularVelocity` rad/s. `Nm` is newton metre per radian, and energy is `J` or `[N*m]`. Power τω, work τθ, τ = Iα and ½Iω² type-check without casts, and the type checker verifies that each `Network` port type's power expression is a power.

An oscillation's angular frequency is an `AngularFrequency` (T⁻¹) and a phase is dimensionless, so ω = √(k/I), the reactance ωL in ohms and `cos(omega * t)` type-check. A rotation becomes a phase only through the constant `radian` or a std function such as `electrical_angle(theta, poles)`. The mp-units page gives angular frequency in rad/s; Ingot keeps rad/s for rotation only (CCR-ING-12).

**Decision D-ING-3:** Plane angle is a base dimension, never cancelled implicitly, and rotational kinds follow the strong angular system: torque in J/rad, moment of inertia in kg·m²/rad², rotational stiffness in J/rad². Oscillation angular frequency is a kind of T⁻¹ and phase is dimensionless. *Why:* with torque in N·m, the laws of rotation each carried a stray radian (R3-29), and angular frequency in rad/s would put one into ωL. *Rejected:* angle dimensionless as in the SI (`3000rpm` would silently become 314 Hz); torque in N·m beside a base angle, the round 1 choice; implicit cancellation at annotations. (revised in round 2)

### Inference and scalar flavors

Every named item states its signature; bodies are inferred bidirectionally. Dimension equations are linear over ℚ, so Gaussian elimination yields a most general solution. F# checks units with integer exponents; Ingot allows rational ones and infers dimension arguments at call sites.

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

Let bindings are not generalized, and lambdas are monomorphic. Integer literals adopt `Int`, `Real` or `Decimal` from the expected type; there is no other implicit conversion between `Int` and `Real`.

A quantity has four flavors, all implementing the trait `Scalar<D>`: exact `Quantity<D>`, `Tol`, `Approx` and `Expr`. Arithmetic and std math are generic over `Scalar`, and a parameter written `Length` accepts any `Scalar<L>` at every call position, in `fn` and `feature` alike. Each call is monomorphized per flavor, and inlay hints show the flavor at each argument.

| Flavor | In the body | Result |
| --- | --- | --- |
| `Quantity<D>` | The value | Exact |
| `Tol<Quantity<D>>` | The nominal; passing the parameter on unchanged forwards its tolerance (D-ING-4) | Exact, unless the parameter itself is returned |
| `Approx<Quantity<D>>` | The value and its budget, propagated by arithmetic | `Approx`; at a feature or operation boundary only `Guaranteed` bounds pass ("Approximate values as inputs") |
| `Expr<Quantity<D>>` | A symbolic value; the body is staged (D-ING-9) | `Expr` |

A parameter that must be exact is written `Exact<Length>`. Three coercions remain: `T` to `Option<T>`, an unkinded quantity to a kind, and a value to an enum variant marked `#[implicit]` (`extrude(10mm)` means `extrude(Blind(10mm))`).

**Decision D-ING-20:** Quantities have four flavors under one trait, `Scalar<D>`. A parameter declared as a quantity accepts every flavor at every call position with one fixed meaning per flavor, and `Exact<D>` opts out. *Why:* round 1 lifted each flavor by its own rule at its own positions, so `rect(other.edge(…).length(), 10mm)` failed to compile and plain functions rejected symbolic values (R3-31). *Rejected:* coercions at feature positions only, the round 1 rule; generic signatures on every helper (ceremony on the commonest code).

### Affine quantities

Absolute temperature is a point, as in mp-units' affine space and Pint's offset units. Point minus point is a difference, point plus a difference is a point, and points never add or multiply.

| Literal or expression | Type |
| --- | --- |
| `20degC`, `68degF`, `absolute_zero + 77K` | `Temperature` |
| `15K`, `27degR`, `5delta_degC`, `t1 - t2` | `TemperatureDifference` |
| `t.absolute()` | `TemperatureDifference` above absolute zero, for radiation and gas laws |
| `200[W/(m*degC)]`, `150[ppm/degC]` | Compound units: `degC` and `degF` inside them mean differences, as datasheets write them |
| `t1 + t2`, `2 * t` | `ING3201`, with fixes `.absolute()` or a difference |

`Tol<P>` and `Approx<P>` for an affine `P` carry their deviations and bounds in `P::Delta`. `Point3` follows the same rules, and gauge pressure is written `p_atm + 2bar`.

Quantities are stored in coherent SI units as binary64, and source keeps literals as written. Display profiles map dimensions to units per package, user or view without changing values. Values print as the shortest round-tripping decimal [unverified: Ryū; paper not opened], and generated literals keep the unit at their position.

### Records, enums, traits and collections

```
pub record DowelSpec { diameter: Length, length: Length, chamfer: Option<Length> = none }
pub enum Extent<Q = Length> { #[implicit] Blind(Q), Symmetric(Q), UpTo(Query<Face>), ThroughAll }

let longer = DowelSpec { ..spec, length: 30mm }        // functional update
let kind = match extent { Blind(d) if d > 50mm => "deep", Blind(_) | Symmetric(_) => "blind", _ => "through" }
```

Records are nominal when declared and structural when written `{ a: Length }`. A structural type may spread another, `{ item: ItemNumber, ..Params<bracket> }`, when shared fields agree (`ING2105`). `Expr<T, Out>` carries the derived outputs its functions declare, so `solve` returns `{ ..Trials, ..Out }` and `result.von_mises` is a typed field (FLX).

Enums are tagged unions with exhaustive `match`, and `#[non_exhaustive]` enums need a wildcard arm outside their package. Type parameters are monomorphized and dimension parameters erased; a bound `D: Dim` passes a dimension when an accessor must check one. Coherence follows Rust's orphan rule, and `dyn Trait` boxes values for heterogeneous lists.

A `Field<D, V>` takes a product domain written as a tuple, `Field<(Body, Time), Temperature>`, and quantity kinds name parameter domains. `kind ParticleRadius: L` thus types a DFN particle concentration as `Field<(Body, ParticleRadius), Concentration>` (D-FLX-38; DFN is phase 5 per contract section 13.4).

| std trait | Implemented by |
| --- | --- |
| `Eq`, `Ord`, `Hash` | Numbers, strings, records and enums by derivation; `Query` by its canonical plan; `Entity<K>` orders by Anvil's canonical geometric order, never by name |
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

`Vec3<Length>`, `Mat3<Stress>` and `Mat<R, C>`, with a dimension per row and column as a Jacobian needs, are std types over the same algebra. A `Range` of quantities iterates only with an explicit step, `(0mm..=10mm).step(2mm)`. `sum`, `min` and `max` use a fixed pairwise tree over indices, and `fsum` returns the correctly rounded sum.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Dimensions and kinds | Rational exponents over eight bases; kinds; erased at run time | `ING3001`, `ING3002` with fixes | ING-O-4 | 0 |
| Strong angular system | Contract section 5 kinds and named units; rotation and phase apart | `ING3001` with a `radian` fix | ING-O-4 | 0 |
| Inference, records, enums, traits | Bidirectional; required signatures; exhaustive `match`; orphan rule | `ING2xxx` | ING-O-5 | 0 (core), 1 (traits, `dyn`) |
| Scalar flavors | One trait, every call position, `Exact<D>` opt-out | `ING2001`; `ING6403` at boundaries | ING-O-5, ING-O-8 | 1 |
| Affine quantities | Points and differences; compound units as differences | `ING3201` | ING-O-4 | 0 |
| `Decimal` and `Money<C>` | Exact at 10⁻⁹; currencies never mix | `ING6101`, `ING2003` | ING-O-5 | 1 |
| Product and parameter domains | `Field<(D, …), V>`; kinds name parameter domains | `ING2001` | ING-O-5 | 1 |

## Tolerances, approximations and truth

| Type | Meaning | Produced by | Consumed by |
| --- | --- | --- | --- |
| `Tol<T>` | Allowed variation of a manufactured characteristic | Designers, fit codes, catalog parts | Geometry (nominal), PMI, variation analysis, checks |
| `Approx<T>` | A computed value and its `ErrorBudget` | Measurements, Field reductions, solves | Checks, reports, explicit decisions |
| `Truth` | `True`, `False` or `Undecided { reason, needed }` | Comparisons of approximate values | `require`, `if`, `match`, query `where:` |

### `Tol<T>`

`Tol<T>` is opaque. It holds a `nominal`, a `center`, `terms` (one deviation coefficient per noise symbol), a `remainder` and its written `form`; `lower()`, `upper()` and `limits()` are methods. `T` is a quantity, `Real` or `Temperature`, whose deviations are `T::Delta`.

| Form | Ingot | Limits |
| --- | --- | --- |
| Symmetric | `4mm ± 0.1mm` | 3.9 mm to 4.1 mm |
| Deviations | `10mm ±(-0.1mm, +0.2mm)` | 9.9 mm to 10.2 mm; signs mandatory |
| Limits | `tol(9.9mm..=10.2mm)` | Nominal at the mid-limit |
| Fit code | `fit(10mm, H7)` | ISO 286-1:2010 tables in `std::mech::fits` (MEC) |
| Basic | `basic(30mm)` | Theoretically exact, toleranced by a GD&T control |

Inverted limits fail with `ING4001` and a deviation of the wrong dimension with `ING4002`; a dimensionless deviation is relative only as a `%` or `ppm` literal.

**Decision D-ING-4:** A `Tol<T>` may be supplied wherever a parameter, record field or enum payload is declared as `T`. The slot holds the nominal and a reference to the tolerance's site: reading it yields the nominal, and passing it on unchanged forwards the reference. Every feature call records the tolerances it receives, for variation analysis, dialogs, PMI and `tolerances(x)`. *Why:* this keeps contract section 6's `thickness: Length = 4mm ± 0.1mm`, carries the tolerance to the call that realizes it as PMI, and keeps geometry at nominal. *Rejected:* a tolerance on every `Length` (temporaries would pay for tracking); `.nominal` at every use (noise, and PMI would lose the tolerance); dropping the tolerance at the first call boundary.

### Arithmetic on tolerances

Each tolerance site (a `±` expression, `tol(…)` or `fit(…)`) owns a noise symbol εᵢ in [−1, 1], and a computed `Tol` is a center plus one coefficient per symbol. In this affine arithmetic (Comba and Stolfi 1993; de Figueiredo and Stolfi 2004), forms sharing a symbol are correlated, which removes interval arithmetic's dependency problem.

| Operation | Result |
| --- | --- |
| `a ± b`, `k * a`, `a / k` with exact `k` | Exact affine combination; `a - a` has zero width |
| `a * b`, `sqrt(a)`, other smooth functions | First-order term per symbol, plus a remainder bounding the rest over the joint box |
| `a < b` and other comparisons | `ING4101`; fixes offer `a.upper() < b.lower()`, `a.nominal < b.nominal` and `yield_of(…)` |

Rounding enters the remainder, so `.limits()` is a guaranteed enclosure in binary64. Statistics are explicit calls that print their assumed distributions: `.rss(k:)` propagates to first order as in JCGM 100:2008, and `.monte_carlo(n:, rng:)` follows JCGM 101:2008. Sites declare distributions with `.statistical(Normal(cp: 1.33))` or an MFG process capability, else `std::tol::default_distribution` applies (normal, limits at ±3σ), and `group:` correlates parts from one reel or fixture.

A symbol stands for one manufactured characteristic:

1. A code-level site has one symbol, so a code-level stack keeps its correlations; a site inside a loop gets one symbol per key.
2. A tolerance forwarded into a Part is keyed by (site, realizing Part or Instance path), so two parts made from one specification vary independently.
3. A tolerance read from geometry (`aspect.size_tol()`, PMI) is keyed by the aspect's `EntityId` and Instance path.
4. `t.independent(key)` makes an independent copy, and `ING-L-SharedSymbol` flags one symbol entering an expression with both signs.

**Decision D-ING-5:** `Tol` arithmetic uses affine forms over per-site noise symbols: worst case by default, exact for linear stacks, with an explicit remainder for nonlinear ones, and statistical only through explicit calls. A site forwarded into a Part takes the Part's path into its symbol. *Why:* linear stacks must be exact and repeated uses of one dimension correlated, while two spacers cut from one specification are two characteristics (R3-30). *Rejected:* interval arithmetic (overestimates repeated dimensions); implicit RSS (hides a process assumption); one symbol per site everywhere, the round 1 rule. (revised in round 2)

MEC's 3D variation analysis uses `tolerances(x)`, which lists the sites behind `x`, and `vary(f, sites)`. The latter replaces chosen sites with samples through literal overrides, so each sample is an ordinary cached evaluation.

A pin in a bore shows a linear stack:

```
pub feature pin_joint(bore_d: Length = 10mm, gap_min: Length = 4um) -> Assembly {
    let bore = fit(bore_d, H7)                   // 10.000 to 10.015 mm [unverified: ISO 286-2 values]
    let pin = fit(bore_d, g6)                    // 9.986 to 9.995 mm [unverified: ISO 286-2 values]
    let h = instance(block_with_bore(d: bore), fixed: true)
    let s = instance(pin_part(d: pin))
    let clearance = bore - pin                   // affine in two symbols
    assembly([h, s], mates: [cylindrical(s.csys("axis"), h.csys("bore"))])
        .require(clearance.lower() >= gap_min, name: "min_clearance")       // 5 um: passes
        .require(clearance.rss(k: 3).hi <= 26um, name: "max_clearance_stat") // 25.75 um: passes
}
```

`clearance.limits()` is exactly 5 µm to 29 µm. Default distributions give σ = 2.5 µm for the bore and 1.5 µm for the pin, so the upper 3σ limit is 17 µm + 3 × 2.92 µm = 25.75 µm. The bore and pin faces receive their fit codes as PMI by forwarding.

### GD&T controls as types

MEC owns the GD&T records, including composite frames, combined zones and size modifiers, and their validators. Ingot owns attachment and the mistakes the type checker catches.

1. **Typed aspects.** `Query<Aspect<K>>` selects shape aspects whose kind is static when the producing feature declares it: `hole(…)` gives `Aspect<OfSize>`, extrude caps `Aspect<Planar>`, recognized imports `Aspect<Any>`.
2. **Controls are values.** `position(…)`, `flatness(…)` and the others return `GeometricTolerance` records whose signatures carry the standards' rules as trait bounds; a material condition modifier needs `K: OfSize`.
3. **Typed attachment.** `part.tolerance(target, control)` attaches the control as an attribute keyed by the target's `EntityId`s. GD&T and PMI attributes use Anvil's split policy `Fail`, so a later split forces re-specification instead of silently creating separate zones.
4. **Dialects are modules.** `std::mech::gdt::asme` implements ASME Y14.5-2018. `std::mech::gdt::iso` implements ISO 1101:2017, ISO 5459:2024, ISO 14405-1:2025, ISO 8015:2011, ISO 22081:2021, ISO 5458 and ISO 2692, whose editions MEC states. The manifest key `gdt-dialect` names the design's dialect, and importing the other fails with `ING4302`.
5. **Tombstones.** Symbols ASME Y14.5-2018 deleted (concentricity, symmetry) are declared `#[removed(in:, instead:)]`, so a call fails with that explanation and fixes.

```
let a = datum("A", plate.face(role: start_cap))
let holes = plate.aspects(created_by: mount_holes)          // Query<Aspect<OfSize>>
plate.tolerance(holes, position(dia(0.1mm), mmc, datums: [a, b, c.at(mmb)]))
// position(dia(0.1mm), mmc, …) on plate.face(role: start_cap)
//   → error ING4201: maximum material condition needs a feature of size; start_cap is Aspect<Planar>
```

Rules that need resolved geometry, such as datum degrees of freedom, run at build time and fail with MEC's `InvalidControl { rule, clause }`. ASME Y14.5.1-2019's page calls it consistent with Y14.5M-1994, so MEC states which governs where it and Y14.5-2018 differ [unverified: alignment with Y14.5-2018].

**Decision D-ING-6:** GD&T controls are ordinary records returned by dialect-specific functions; legality rules are trait bounds on typed aspects where the kind is static, and the rest run at build time. *Why:* the commonest GD&T errors (material modifiers on surfaces, deleted symbols, mixed dialects) become compile errors at their line. *Rejected:* a GD&T sublanguage (a second grammar for a few dozen records); validation only at build time (late, far from the cause); string-encoded feature control frames (untyped).

### `Approx<T>` and the decision rule

`Approx<T>` is a value with an `ErrorBudget<T::Delta>` (contract section 5) whose parts use only `Pointwise` and `Goal` norms, plus flags such as `Singular`. Measurements (`body.volume()`, `distance(a, b)`), Field reductions (`stress.max(over: R)`) and Wasm component results with declared errors return it. A reduction is `Quantified` only when Flux estimated that functional; otherwise its discretization part is `NotQuantified`.

Arithmetic propagates each source separately with outward rounding, keeping the product term (|xy − x̃ỹ| ≤ |x̃|·e_y + |ỹ|·e_x + e_x·e_y). Bounds in one norm add, different norms never combine, and a part's kind is the weakest of its inputs. Division by an enclosure containing zero fails with `ING6104`.

One rule decides every comparison of approximate values, in `if`, `match` guards, query `where:` and `require` alike. For `x < y` with the evidence level `e` (`Estimated` unless a check declares `Guaranteed`):

| Outcome | Condition |
| --- | --- |
| `True` or `False` | Every part is quantified and meets `e`, the enclosures are disjoint, and no blocking flag is set |
| `Undecided { WithinBound, needed }` | The enclosures overlap; `needed` is the bound that would decide |
| `Undecided { Indicator }` | A part is only an `Indicator`, as every `Preview` result is |
| `Undecided { Unquantified(sources) }` | A part is `NotQuantified` (for `require`, see "Checks" for the conditional `Pass`) |
| `Undecided { SingularPoint }`, `Undecided { Flagged(flag) }` | A blocking flag from the producer |

`==` on an `Approx` is `False` on disjoint enclosures and `Undecided` otherwise. `and`, `or` and `not` follow Kleene's strong three-valued logic, so `False and Undecided` is `False`.

Each node records the fidelity of the bounds it observed. Below the Evaluation's fidelity ceiling, an `if`, `match` or `where:` on `Undecided` yields `ResultStatus::Pending` and waits for the next fidelity's node, which Kiln has already demanded. At the ceiling it fails with `ING6401 UndecidedBranch`, carrying the margin and the accuracy needed.

**Decision D-ING-7:** Comparisons of approximate values return a three-valued `Truth` by one rule: disjoint enclosures decide, subject to the declared evidence, and `Indicator` or `NotQuantified` parts never decide. Control flow on `Undecided` waits as `Pending` below the fidelity ceiling and fails with `ING6401` at it. *Why:* four tabs had four rules (R3-07); comparing estimates passes designs within numerical error; waiting spares branches evaluated at `Interactive` (R3-14). *Rejected:* comparing estimates only; a consumer-side margin rule; treating `Undecided` as `False`; failing at every fidelity. (revised in round 2)

`body.volume().estimate()` discards a bound explicitly, and the language service marks it.

### Approximate values as inputs

Geometry is often driven by measured geometry, as in `rect(other.edge(role: side(r.top)).length(), 10mm)`. At a feature or operation boundary, an `Approx` argument passes only with a `Guaranteed` total: the call uses the value and records the bound in an `InputSensitivity` record, which variation analysis reads.

Weaker bounds fail with `ING6403 EstimateAsInput`, whose fixes declare the parameter `Approx<T>` or write `.estimate()`. Representation error stays in Anvil's per-face bounds, so `body.convert(into: Mesh, tolerance: 0.01mm)` returns a `Body`.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `Tol<T>` forms and forwarding | Opaque affine form; nominal in slots; sites recorded per call | `ING4001`, `ING4002` | ING-O-7 | 1 |
| Affine tolerance arithmetic | Exact linear stacks; guaranteed enclosures; symbols keyed by realizing Part | `ING4101`, `ING4102`; `ING-L-SharedSymbol` | ING-O-7 | 1 |
| Statistical combination | Explicit `rss` and `monte_carlo`; declared distributions and groups | Assumptions printed | ING-O-7 | 1 |
| GD&T attachment and dialects | Typed aspects, dialect modules, tombstones, split policy `Fail` | `ING42xx`, `ING4302`, MEC `InvalidControl` | MEC-O-TL-1, ING-O-5 | 1 |
| `Approx<T>` | `ErrorBudget<T::Delta>` in `Pointwise` and `Goal` norms; outward rounding | `ING6104` | ING-O-8 | 1 |
| Decision rule | Disjoint enclosures decide under declared evidence; Kleene logic | `Undecided { reason, needed }` | ING-O-8 | 1 |
| Pending branches | `Pending` below the ceiling; `ING6401` at it | `ING6401 UndecidedBranch` | ING-O-35 | 1 |
| Approximate inputs | `Guaranteed` only; bound into `InputSensitivity` | `ING6403` with two fixes | ING-O-8 | 1 |

## Geometry in the language

### Kiln-held values

`Body`, `Part`, `Assembly`, `Instance`, `Field` and `Material` values are immutable handles to values Kiln holds and the CAS stores. Code calls operations and std features that return new handles, and handle equality is content equality (`ObjectId`).

| Type | Created by | Key members (std) |
| --- | --- | --- |
| `Body` | Operations and features; `+`, `-`, `&` | `faces`, `edges`, `regions`, `aspects`, `volume`, `bbox`, `mass_properties`, `convert(into:)` |
| `Part` | `part(body, name:, item:)` | `.body`, `.material`, `.material(m)`, `.tolerance(target, control)`, `.require(…)`, `.csys(name)`; a property of an unassigned material fails with `ING6701` |
| `Assembly` | `assembly(instances, mates:)` | `.instances()`, `.find(path)`, `.bom()`, `.interference()` |
| `Instance` | `instance(part_or_assembly, at:, fixed:)` | `.part`, `.placement`, `.csys(name)`, `.path` |
| `Field<D, V>` | Flux operations and std physics | Defined by FLX |

A chain such as `a + b + c` lowers to one n-ary `anvil::boolean` by a fixed rule of the language behavior version, so one source always gives one operation graph. The prelude defines `origin`, the directions `x`, `y` and `z`, the axes and the planes `plane.xy`, `plane.yz` and `plane.xz`. Reference geometry (`plane.offset`, `plane.mid`, `axis.of`, `point.on`) is MEC's `std::mech::refgeom`, phase 1, returning `CoordSys`-anchored values re-resolved through their queries.

### Call sites and names

An `Entity<K>` is a Body's `ObjectId` plus an `EntityId`, valid only with its Body; its accessors (`e.area()`, `e.normal(at: p)`) return `Approx` values. Anvil names entities by `OpSite` (D-ANV-14), which Ingot derives from source text alone (contract section 5). An `OpSite` is the path of call frames from the Evaluation's root, outermost first; each frame, a feature or `fn` call, has three parts.

| Part | Rule | Stable under |
| --- | --- | --- |
| Statement | A `let` is (item path, arm path, binding name); an unnamed statement is (item path, arm path, nearest preceding binding name, ordinal after it). An arm path names `then`, `else`, a `match` arm by its pattern's canonical text, or `block` and `body` | Edits elsewhere, moves, reformatting, literal and argument edits, retyping the statement |
| Call | The operation or feature name and its occurrence index among calls of that name in the statement | Appending, wrapping or inserting calls of other names; a same-name call renames only later ones of that name |
| Keys | One key per enclosing iteration ("Patterns, loops and keys") | Inserting or removing other elements |

Renaming a binding is a refactor that writes `#[was(old_name)]`, keeping the identity until a person removes the attribute. Live-collaboration block ids map onto these identities and never enter them (KLN). Since identities come from text alone, a Git round trip or a publication leaves every `EntityId` unchanged.

**Decision D-ING-21:** `OpSite`s derive from source text: a path of frames, each with a statement identity from binding names, a call identity from the callee's name and occurrence, and iteration keys. *Why:* block ids changed after a Git round trip, a retyped statement or publication (R3-06, R2-02), and slot paths renamed every pipeline stage when one was appended (R2-06). *Rejected:* live-document block ids, the round 1 rule; slot paths; source offsets or evaluation order; a CRDT identity per call (not derivable from text).

Nothing in Ingot orders, numerically hashes or prints names. `Entity<K>` compares by equality and orders by Anvil's canonical geometric order, and `Seed::from(x)` hashes `x`'s encoding with names removed. Geometry and check values therefore depend only on text and inputs, as label invariance requires (contract section 7.1).

A transform (`move`, `rotate`, `mirror`, `transform`) whose source binding is used again, or written `copy(x)`, creates copies whose entities take role `copy` or `mirror`. The compiler knows reuse from the IIR's data flow, and a transform that replaces its source keeps names. `seed.face(role: top).copies()` follows copies on request, and role queries on reflections accept `mirrored: true` (D-ANV-30).

### The query language

A `Query<K>` describes a selection on a subject Body and re-resolves wherever it is used. It is built by methods on a Body, Part, Instance or another query; `Query<Point>` also covers derived points such as `face.corners(inset:)`.

| Element | Syntax | Meaning |
| --- | --- | --- |
| Subject and count | `b.face(…)`, `b.faces(…)`, also `edge`, `vertex`, `region`, `aspect` | Singular needs one match; plural at least one unless `count:` says otherwise |
| Anchor | `part.face(base.face(role: end_cap))` | Descendants of the anchor through Anvil's lineage |
| Role | `role: end_cap`, `role: side(outline.top)` | Entities created with that role; roles are constants a feature declares with `#[roles(…)]`, hashed by fully qualified path |
| Creator, history | `created_by: holes`; `new`, `modified`, `all` | Entities from the call site that produced `holes`; created or modified by the operation that produced the subject value |
| Geometric filters | `normal: +z`, `kind: Cylinder`, `area: 100mm2..`, `radius: 2.95mm..=3.05mm`, `radius: near(3mm, within: 0.05mm)`, `parallel_to:`, `within:` | Certified predicates; a `Tol` argument fails with `ING4103`, whose fix rewrites it as a range, so a selection never becomes a manufacturing tolerance |
| Topology | `.edges()` of a face query, `adjacent_to:`, `bounded_by:` | Adjacency in the subject |
| Rank selectors | `longest`, `largest`, `nearest: p`, `first(along: d)`, `last(along: d)` | Only after an anchor or role filter, else `ING-L-FragileSelector`; a winner whose lineage changes inside the declared ranges gets `Note::RankSwap { at }` |
| Set algebra | `q1 + q2`, `q1 - q2`, `q1 & q2` | On one subject |
| Custom filter | `where: \|f\| f.area() > 2 * hole_area` | An Ingot predicate; `Undecided` fails with `ResolveError::Ambiguous` |
| Merges | `on_merge: Accept` | Where the operation declares an extent use, a merged anchor fails with `ResolveError::Merged` unless written |

```
let bores  = body.faces(kind: Cylinder, radius: 2.95mm..=3.05mm, created_by: holes)
let rim    = top.edges() - top.edges(adjacent_to: bores)
let lip    = body.edge(created_by: base, role: side(any), last(along: +z))   // rank after an anchor
let blends = body.faces(new)
```

A query resolves on the Body of the operation that consumes it, mapping its selection through lineage, so `fillet(solid, base.face(role: end_cap).edges())` works. A `Query` parameter resolves on the first `Body` or `Part` parameter unless `#[on(param)]` names another. Ingot lowers each query to a canonical `QueryPlan` that `anvil::resolve` evaluates as its own node, so selections cache separately and a `ResolveError` arrives at the query's span with ranked fixes.

There is no positional access (`ING5001`). `.resolve()` returns entities in canonical geometric order, `sorted_by` in a stated order, and `e.query()` anchors a query on one entity's `EntityId`.

**Decision D-ING-8:** Queries are values built from named arguments and resolved by a separate `anvil::resolve` node. Geometric filters are declarative ranges that Anvil certifies, rank selectors apply only after a provenance anchor or role filter, and arbitrary predicates are an explicit `where:` closure whose undecided outcomes fail. *Why:* declarative filters can be certified, cached and explained; anchored ranks cannot silently swap winners within declared ranges (R2-22). *Rejected:* string selectors such as CadQuery's `">Z"` (untyped); build123d-style sorting and slicing (positional); unanchored rank selectors, allowed in round 1. (revised in round 2)

### Builder blocks and sketches

A call may end with a block, as in `sketch(plane.xy) { outline }`, Swift's result-builder mechanism with a smaller rule. A function opts in with a final `Builder<I, Ctx>` parameter, and each expression statement whose type implements `Emit<I>` contributes its items in order (`ING2301` otherwise). A `let` also names its items as result fields, so a block with `let r = rect(…)` is a `Sketch<{ r: Rect }>`.

`if`, `match` and `for` contribute their branches' or iterations' items. Receiver members shadow prelude names, and a clash with an enclosing binding is `ING1104`. ELX's `network { … }` uses the same mechanism with set-like accumulation.

Inside a sketch, entities are symbolic: `line(p0, p1)` creates unknown points seeded at `p0` and `p1`, accessors return `Expr<Length>`, and constraints are items. `e1 == e2` builds an `Equation`, as Flux's weak forms do. A helper's named sub-entity becomes the role argument of what is swept from it, so `side(outline.top)` names the face an extrude sweeps from that edge.

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

`chord_ratio`, an ordinary function over `Length`, accepts `Expr<Length>` (D-ING-20). Branching on a symbolic value fails with `ING2402`, and `select(cond, x, y)` builds conditional residuals. Seeds are literals that a sketch drag rewrites on release (UIX); a build never warm-starts from an earlier solve (MEC).

Constitutive code never differentiates through loops: `local_solve(residual, x0)` writes a local Newton solve, differentiated by the implicit function theorem (contract section 6).

`anvil::solve_constraints` solves a sketch block's constraint system as one node. A solved point is an `Approx<Point3>`, `Guaranteed` when Anvil's Krawczyk test proves its block and `Estimated` otherwise. SketchGraphs offers "15 million sketches extracted from real-world CAD models", and ING-O-23 converts a fixed sample into sketch blocks.

**Decision D-ING-9:** Constraints, analytic Field expressions and weak forms are one mechanism: staged symbolic values (`Expr<T>`, `Equation`, Flux's form types) built by ordinary functions and handed over as a hash-consed expression DAG. Any function over quantities works on symbolic values, because quantity parameters accept every `Scalar` flavor. *Why:* one mechanism serves MEC's constraints, FLX's constitutive functions and analytic Fields, and equal expressions become equal keys. *Rejected:* a `constraint` keyword with its own subset; tracing arbitrary code into the kernel IR (branches on unknowns would be captured for one value). (revised in round 2)

### Assemblies, variants and families

An Instance's path lists instance names from the root (`drive/wheel`). A query through an Instance carries its placement, so measurements between Instances are in assembly coordinates; mates take `CoordSys` values (MEC). A record marked `#[interface]` derives a `compatible(a, b)` check.

Variants are enum or record parameters marked `#[configuration]` on assembly features (contract section 6). Conditional regions that depend only on configuration parameters and constants are variant regions, and Instances created inside carry the region's condition. Creating an Instance under any other condition, including a loop over a computed count, fails with `ING2601`, so Kiln computes the 150% BOM by abstract interpretation with SAT checks (KLN).

**Decision D-ING-22:** Variant parameters are ordinary parameters marked `#[configuration]`, and an Instance's existence may depend only on them and on constants, checked at compile time. *Why:* the 150% BOM needs a static account of which Instances exist under which options, and plain `if` let existence follow computed geometry (R3-18). *Rejected:* `options` and `when` keywords (contract section 6 forbids domain keywords); enumerating configurations (exponential).

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

A `CatalogSelection` is a pure function over pinned definition packages, plus pinned offers when it ranks by price or stock (ELX). It re-resolves whenever its arguments change, while `crucible update parts` refreshes only the data pins and lists substitutions. `?` turns `NoCatalogMatch` into a failure whose fixes are the nearest candidates, and editing `speed` re-evaluates only `bearing_speed`.

A feature's parameter list is a record type, `Params<f>`, whose defaulted fields may be omitted, and a call spreads a record into named arguments. A design table is a table of parameter records (D-MEC-10):

```
let b = bracket(..heavy, width: 90mm)                     // later arguments override the spread
pub let brackets = family(bracket, key: |r| r.item, rows: table {
    item     | width | thickness     | load
    "BR-060" | 60mm  | 4mm ± 0.1mm   | 1.2kN
})
```

A table row's type is `{ item: String, ..Params<bracket> }`. `table("brackets.csv")` reads a repository file as a source input whose header names units (`width [mm]`), and a mismatched cell fails with `ING3501 UnitMismatch { column, expected }` at its file position.

### Patterns, loops and keys

A pattern is a feature whose instances differ only in their keys, and a `for` loop yields a list, so per-instance variation is ordinary code. Iteration contributes keys, never positions (contract section 5):

- iteration over entity lists or resolved queries keys by `EntityId`;
- MEC's generators return keyed lists: `linear` by `(i, j)`, `circular` by angular index, `at_points` by anchor `EntityId`, `fill` by lattice coordinates, `by_density` by each seed's initial key;
- integer ranges and literal lists keep integer keys, and `keyed(xs, by: f)` keys any list, failing with `ING6202 DuplicateKey` on a repeat;
- `ING-L-PositionalKey` warns when a computed list whose length depends on geometry is iterated by position.

Pattern `skip:` lists take keys, not indices (MEC). There is no mutable accumulator; `fold` and `scan` carry running state, and a loop over quantities needs an explicit step.

```
let vents  = pattern(vent_slot(length: 10mm), at: linear(dir: +x, count: 8, spacing: 6mm))
let graded = for i in 0..8 { vent_slot(length: 10mm + i * 2mm) |> move(x: i * 6mm) }
```

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Kiln-held values and Booleans | Handles compared by `ObjectId`; n-ary lowering by a fixed rule | `ING6701` | ING-O-1 | 0 |
| Text-derived `OpSite` | Frame path of statement, call and keys; `#[was]` renames | `ING1102` for duplicate names | ING-O-25, ANV-O-SITE-1 | 0 |
| Label invariance in the language | No order, numeric hash or printing of names; label-free seeds | Not expressible | ANV-O-LABEL-1 | 0 |
| Copies and placements | Reuse or `copy` creates `copy` and `mirror` roles; `.copies()` | — | ANV-O-COPY-1 | 1 |
| Queries | Canonical plans resolved by `anvil::resolve`; anchored ranks; ranges, not tolerances | `ResolveError` with fixes; `ING4103`, `ING5001`; `ING-L-FragileSelector` | ING-O-11, ANV-O-NAME-2 | 1 |
| Builder blocks and sketches | `Builder<I, Ctx>`; symbolic entities; named sub-entities; certified solved points | `ING1104`, `ING2301`, `ING2402` | ING-O-5, ING-O-23, ANV-O-NAME-5 | 1 |
| Variant regions | Instance existence from configuration parameters and constants only | `ING2601` | ING-O-30 | 1 |
| Catalog selections | Pure over pinned data; re-resolve on argument change | `NoCatalogMatch` with candidates | ING-O-13 | 1 |
| Families and tables | Record spread, table literals, CSV with unit headers | `ING2105`, `ING3501` | MEC-O-PF-12 | 1 |
| Keyed iteration | Keys from entities, generators, ranges and `keyed` | `ING6202`; `ING-L-PositionalKey` | ING-O-26 | 1 |

## Evaluation

### Calls and effects

Every Ingot call is pure. Calls differ in cost and in whether Kiln memoizes them, and the kind of a call is visible in its declaration. A `feature` may return any type; it is the unit of history and caching, and a `fn` is not.

| Call kind | Declared with | Kiln node |
| --- | --- | --- |
| Function | `fn` | None; the executor calls it directly |
| Memoized function | `#[memo] fn` | Keyed by code hash and arguments only; may not call operations or features (`ING2501`) |
| Feature | `feature` | Feature node, keyed with its `OpSite` |
| Operation | `extern fn` with `#[op("anvil::blend")]` | Op node keyed by `OpKey` |
| Wasm component export | `extern fn` with `#[component(…)]` | Op node whose implementation is the Wasm component |
| External Op | `extern fn` with `#[external(…)]`, declared by its package (ECO) | Op node on untrusted-evaluation workers (contract section 7.8) |
| Query resolution | Implicit where a `Query` reaches an operation | Resolve node |
| Check | `require` | Check node |

Operations, Wasm component exports and External Ops are the only engine effects: pure in meaning, expensive, asynchronous and cached. `ingot-bindgen` generates `std::ops::anvil` and `std::ops::flux` from Anvil's and Flux's operations catalogs, and any package may write its own `extern` declarations, each checked against the catalog (`ING8001`). Source never names a behavior version; `ingot.lock` pins one per operation.

**Decision D-ING-10:** Ingot has no user-visible effect system. Operations are pure calls, and the side channels (checks, notes, tolerance sites, PMI) are write-only accumulators ordered canonically by call site, like Salsa's accumulators. *Why:* effect annotations would describe effects the language forbids, and canonical order makes accumulators independent of evaluation order. *Rejected:* an effect-row type system (no effects to track); FeatureScript-style `context` and `id` threading (boilerplate for an order the dataflow already fixes).

### Determinism and randomness

Contract section 7.3 owns the determinism rules, PLT the mechanisms (`detmath`, no implicit FMA, canonical reduction order) and KLN the policy. Ingot adds these language rules:

- strict left-to-right evaluation, checked `Int` overflow, and no NaN or infinity values (`ING6102`);
- ordered maps and sets, stable sorts, and no `Real` map keys (`q.key(resolution: 1um)` quantizes);
- NFC strings without locale; nothing ordered or hashed by name; labels invisible to code, since Kiln joins them;
- no time, environment, files or network: sources, tables, Assets and External inputs are Kiln input cells read by content.

Randomness is a value. `Rng` keys Philox, Salmon and colleagues' counter-based generator, in its 4×32 form with 10 rounds [unverified: variant and round count]. The n-th number is a pure function of key and n, so streams split and run in parallel without changing any value.

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

`Failure` is an extensible union [unverified: OCaml manual not opened]: every enum implementing `Error` adds its variants, and a match over `Failure` needs a wildcard arm.

An `Abort` is environmental: cancellation, resource exhaustion, device loss, budget exhaustion, worker loss, or Kiln's demand-depth and Evaluation fuel limits (contract section 2). It is not a `Failure`, and `try` cannot observe it. It propagates to every transitive dependent, and no node that observed one writes a memo entry, CAS object or attestation (contract section 7.2).

**Decision D-ING-11:** Deterministic failures propagate to the nearest `try` or feature boundary and become cached values there, and `try` converts them into `Result` for recovery. Aborts are not values, and no Ingot construct observes them. *Why:* forcing `?` onto every geometry call adds noise without information, and a fallback taken because a worker ran out of memory would be cached as geometry (R3-03). *Rejected:* `Result` on every operation; untyped exceptions; catching every failure kind, the round 1 rule. (revised in round 2)

A feature's checks are evaluated against its result; when the feature fails, they report `Error(DependencyFailed)`. A failure inside one Instance never erases sibling work.

### Limits

Every node ends in a value or a typed `Failure`, and every Evaluation ends or aborts. Per-call limits are counted in units the language defines; the cost table belongs to the language behavior version.

| Limit | Unit | Default per feature call | Failure |
| --- | --- | --- | --- |
| Fuel | Steps of the cost table | 10⁹; `#[fuel(…)]` raises it up to the manifest maximum | `ING6301 FuelExhausted` |
| Call depth | Ingot frames | 2,048 | `ING6302 DepthExhausted` |
| Memory | Semantic bytes: 8 per scalar or handle, 16 per collection header | 1 GiB | `ING6303 MemoryLimit` |
| Operation calls | Count | 10⁶ | `ING6304 TooManyOperations` |
| Symbolic expression size | DAG nodes | 10⁷ | `ING6305 ExpressionTooLarge` |

A call's steps include the plain functions it calls, while feature and `#[memo]` calls are nodes with their own limits. An outcome therefore never depends on the caller's remaining budget or on the cache, and an operation call charges 100 steps plus 1 per marshalled element. Effective limits are a function of source and manifest only, and they enter the node key.

Kiln adds two evaluation-wide limits as Aborts: 10,000 nested node demands, so `f(n) = f(n + 1)` aborts with `DemandDepthExhausted`, and a fuel governor per Evaluation from its budget. An organization ceiling below a requested limit refuses the Evaluation at admission with the Abort `FuelCeilingExceeded`, never a cached `FuelExhausted`. A host out of memory below the semantic limit raises the Abort `ResourceExhausted`.

**Decision D-ING-23:** Per-call limits come from source and manifest only and enter the node key; evaluation-wide limits and policy ceilings act only as Aborts. *Why:* a limit clamped by policy made two organizations cache different results for one key (R3-12), and per-call limits alone let a self-calling feature build an unbounded chain of nodes (R3-04). *Rejected:* organization ceilings inside the limit; per-call limits as the only bound; wall-clock limits (nondeterministic, so they exist only as cancellation).

`#[suppressed]` on a `let` removes the call. A pipeline statement whose input and output types agree then binds its input, as CAD users expect, and other uses fail with `ING6601 Suppressed`. Rollback is the request `EvalRequest { target, until: statement }`, never a source edit.

### The Ingot IR and Kiln

Lowering produces the Ingot IR (IIR), a dataflow graph in the style of the regionalized value state dependence graph (RVSDG), whose "regions capture the hierarchical structure of programs". Ingot is pure, so the IIR has no state edges.

| IIR construct | Meaning |
| --- | --- |
| Simple node; Kiln call node | Plain computation; an Op, resolve, feature or check call with its `OpSite` |
| γ, map and fold, λ and φ regions | Conditionals; loops carrying keys; functions and recursive groups |
| Observation edge | Where the executor needs a Kiln-held value's content |

Spans live in a side table, so an edit above a function leaves its IIR unchanged. Each module's code hash is a SHA-256 Merkle hash over its IIR and the code hashes of the modules it uses.

1. **Front-end nodes.** Kiln keys each module's front end by module identity and compiler behavior version. Parse, items, signatures, bodies and IIR are memoized stages that backdate, so a comment edit stops at the IIR.
2. **Feature nodes.** A feature call's key follows contract section 7.2: the code hashes of the modules it used, the language behavior version, argument identities, the effective fidelity and its `OpSite`, plus its effective limits. Its value splits into outputs with their own change markers: the result, one per accumulator kind, and metadata (fuel, cost). Dependents record which outputs they read, and metadata never enters backdating, so a fuel-only edit re-executes nothing downstream.
3. **Asynchronous calls.** The executor issues each Kiln call, receives a pending handle at once and suspends only at observation edges, so independent calls run in parallel. Kiln prefetches the calls the IIR lists as known before any observation.
4. **Program order.** Each call records its program-order index. When several calls fail, the outcome is the earliest in program order, and speculative work after it never changes a result.
5. **Overrides.** A request may carry literal overrides keyed by `LiteralSite` (statement identity, call identity, argument slot). Kiln treats them as input cells, so a drag evaluates new values without editing source (UIX); a wrongly typed override fails with `ING6502`.

[[DIAGRAM: Ingot pipeline. Left column "Front end (Kiln nodes)": source text → lossless tree → typed AST → names, types, units, tolerances → IIR (spans in a side table) → module code hashes. Middle column "Executor": IIR → reference interpreter in the canonical class; a dashed box "code generator, phase 2 at the earliest" with a dashed "differential oracle" arrow. Right column "Kiln": interpreter issues Op, resolve, feature and check calls as pending handles → Kiln schedules Anvil, Flux and Wasm component Ops → values return at observation edges → node outputs: result, accumulators, metadata. Bottom arrows: "literal overrides (drag)" into the executor; "statement, call and keys → OpSite" from the tree into Kiln calls.]]

### Fidelity, drags, holes and derivatives

Ingot code cannot observe fidelity, so every fidelity runs the same program; a check's `fidelity:` names the fidelity of its own check node. A release demands every node at `SignOff`, geometry included, so released checks never read geometry that only a lower fidelity built.

When a drag starts on a literal, Ingot compiles a residual program over the literal's forward slice, with everything else a constant from the current evaluation; its outputs equal the full program's (ING-O-12). Unfinished code becomes typed holes that evaluate to `ING6001 Incomplete`, and evaluation proceeds around them as in Hazel's live semantics, keeping the viewport live.

Derivatives serve UIX's edit plans and Flux's `grad(J, wrt: [p1, p2])`, whose `wrt:` names parameters or literal bindings. Data dependence plus provenance gives the literals that can affect an entity, exactly and cheaply. Forward mode uses dual numbers and each Op's tangent rule, reverse mode Kiln's `Differentiable` operations and reverse traversal (KLN); an Op without a rule fails with `NotDifferentiable { op }`, and `fd_grad` is an explicit, labelled estimate.

In phase 1, edit plans rank by provenance first: the literal of the call whose `OpSite` and role created the dragged entity, such as an end cap's extrude distance. IIR dependence distance comes next, and derivatives refine the ranking from phase 2, when `anvil::shape_velocity` lands.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Calls and accumulators | Eight call kinds; canonical accumulators as separate outputs | `ING2501`, `ING8001` | ING-O-13 | 0 |
| Determinism and randomness | Bit-identical values, failures and fuel; keyed Philox streams | Aborts never cached | ING-O-1, ING-O-6 | 0 |
| Failures and Aborts | `try` catches `Failure` only; Aborts write nothing | Typed `Failure`; `DependencyFailed` | ING-O-1, ING-O-24 | 0 |
| Per-call limits in keys | Limits from source and manifest; ceilings at admission | `ING63xx`; Abort `FuelCeilingExceeded` | ING-O-28, ING-O-6 | 0 |
| Evaluation-wide limits | Demand depth and fuel governor as Aborts (KLN) | Abort `DemandDepthExhausted` | ING-O-24 | 0 |
| IIR and the Kiln contract | Module code hashes; split outputs; pending handles; program order; overrides | `DependencyFailed`; `ING6502` | ING-O-13, ING-O-27 | 0 |
| Suppression and rollback | Binding takes the pipeline input; rollback as a request | `ING6601` | ING-O-10 | 1 |
| Drag specialization | Residual program on the forward slice | Falls back to full evaluation | ING-O-12 | 1 |
| Holes | Evaluation around holes | `ING6001` | ING-O-15 | 1 |
| Derivatives | Dependence and provenance ranking (1); forward and reverse modes (2) | `NotDifferentiable { op }` | ING-O-16 | 1, 2 |

## Diagnostics and checks

### Diagnostics

Compile-time diagnostics and evaluation failures share one structure, so the UI, the CLI and agents handle them alike.

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

`Applicability` is `MachineApplicable`, `MaybeIncorrect` or `HasPlaceholders`, and `SourcePatch` is the record AGT's edit methods take. Query fixes carry Anvil's stability ranking over the full declared parameter ranges (ANV).

| Codes | Area | Examples |
| --- | --- | --- |
| ING0xxx | Lexing and parsing | `ING0002` non-NFC source; `ING0003` hidden characters |
| ING1xxx | Names and modules | `ING1001` unknown name, with nearest names; `ING1104` builder name clash |
| ING2xxx | Types and traits | `ING2001` mismatch; `ING2402` branch on a symbolic value; `ING2601` Instance under a computed condition |
| ING3xxx | Units and kinds | `ING3001` dimensions; `ING3002` kinds; `ING3201` affine misuse |
| ING4xxx | Tolerances and GD&T | `ING4101` comparison of tolerances; `ING4201` material condition on a non-size aspect |
| ING5xxx | Geometry references | `ING5001` positional entity access |
| ING6xxx | Evaluation failures | `ING6001` incomplete code; `ING6301` fuel; `ING6401` undecided branch |
| ING7xxx | Packages and lockfile | `ING7001` unresolvable dependency with PubGrub's explanation |
| ING8xxx | Bindings | `ING8001` extern signature differs from the catalog |
| `ING-L-<Name>` | Lints | `ING-L-FragileSelector`, `ING-L-PositionalKey`, `ING-L-SharedSymbol` |

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

An evaluation `Failure` adds the feature call chain, the entities involved and an optional cause. Anvil's `ResolveError` fixes and MEC's `FeatureError` fixes arrive as `Fix` values, so a person clicks them and an agent applies them without translation. The interpreter checks non-finite values, fuel and depth after every step, so it reports the exact expression.

### Checks

`require` declares a check: a predicate with a severity, a fidelity, an evidence level and a source. It never changes the value it attaches to, and its predicate runs as a separate check node after the geometry it reads.

```
require stress < 0.6 * sy, severity: Error, fidelity: SignOff, evidence: Estimated,
        name: "static_margin", because: "allowable of 0.6 Sy for this bracket class"
part.require(part.mass() < 120g, severity: Warning)       // attaches to the Part and returns it
```

| Field | Default | Meaning |
| --- | --- | --- |
| `severity` | `Error` | `Error` blocks protected merges and releases; `Warning` and `Info` report |
| `fidelity` | `SignOff` | The fidelity a release or protected merge evaluates; lower outcomes are provisional |
| `evidence` | `Estimated` | The weakest bound kind that may decide: `Estimated` or `Guaranteed` |
| `name` | From the predicate's source | Identity across edits; Kiln's diff and merge match checks by it |
| `because` | none | Rationale for reports and agents |

A `require` statement attaches to its feature call, a module-level one to the design, and `x.require(…)` to `x`, carrying it into assemblies with the Instance path in its identity. A comparison chain records value, limit and margin, and a conjunction one sub-outcome per conjunct. "Provisional" means fidelity below the declared one, never a verdict.

The outcome is contract section 5's `CheckOutcome`, decided by the rule in "`Approx<T>` and the decision rule". When some parts are `NotQuantified` but every compared value's discretization part is quantified, the rule decides on the quantified parts: a `Pass` lists the unquantified sources in `conditional_on`, and a `Fail` stays `Fail`. A conditional `Pass` meets a release gate only when repository policy names a cited covering allowance for each source; the check then re-evaluates with it as a declared `Estimated` part, and without one the verdict is `Undecided { Unquantified(sources) }`.

When no study estimates a check's functional, the language service offers a visible fix adding it to the study's `goals:` (D-FLX-5).

A `require` in a file under the protected `oracles/` directory has the source `Protected(path)`, which agents cannot edit; every other check has `Declared(span)`. A waiver is an attribute, `#[waive(check: "static_margin", reason: "…", until: "C")]`, shown in reviews and never applicable to `Protected` checks.

```
use std::sim::quick::static_stress

pub feature bracket_check(b: Part, clamp: Query<Face>, pad: Query<Face>, load: Force = 1.2kN) -> Part {
    let study = static_stress(b, fixed: clamp, force: load, on: pad)
    let peak = study.von_mises.max(over: b.away_from(clamp, 8mm))     // Approx<Stress>
    b.require(peak < 0.6 * b.material.yield_strength(at: 20degC), name: "static_margin")
}
```

| Situation, with an illustrative limit of 0.6 × 276 MPa = 165.6 MPa | Outcome of `static_margin` |
| --- | --- |
| `Preview` result | `Undecided { Indicator }` |
| `Interactive`: 112 MPa ± 20 MPa, `Estimated { calibration }`; model form `NotQuantified` | Enclosures disjoint: a provisional `Pass { conditional_on: [model form] }` |
| `SignOff`: 118 MPa ± 1.5 MPa `Estimated`; model form `NotQuantified` | `Pass { conditional_on: [model form] }` |
| Same, with a policy allowance citing a design-code partial factor | `Pass` |
| The region comes within the exclusion distance of a flagged singular edge | `Undecided { SingularPoint }`, with fixes to widen the exclusion or add a fillet |
| The solve does not converge | `Error(failure)`, with the solver's diagnostics |

**Decision D-ING-12:** Checks are declarations evaluated as separate nodes, never inline assertions: a failing or undecided check does not stop geometry, and a feature cannot branch on a check's outcome. *Why:* designers need to see the geometry that fails; expensive predicates run after geometry at lower priority; and adding a check never changes a design or a solve, since study goals are explicit inputs (D-FLX-5). *Rejected:* assertions that abort evaluation (hide the failing geometry); checks as Booleans in the dataflow (a check could alter geometry and invalidate caches).

### Free text

The lossless tree classifies every span as free text or structure. Comments, doc comments, string literals and description templates are free text, as is any identifier that neither the compiler produced nor a human typed. `repo` records which context wrote each span (KLN), and AGT's `read.source`, `read.outline`, `read.docs` and `inspect.describe` return a free-text span as an `ExternalText` handle when its author is outside the reader's delegation chain or untrusted.

A human merge endorses structure and typed values, never free text (contract section 7.6). Per-span endorsement shows the text verbatim, and `ING0003` already keeps hidden characters out of source.

**Decision D-ING-24:** The syntax tree classifies every span as free text or structure, and only structure is endorsed by merging. *Why:* an agent could address a later reader through a merged comment, identifier or description template (R5-02). *Rejected:* wrapping only imported strings in `external(…)`, the round 1 rule; banning comments from agents (they document real intent).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Diagnostics and fixes | One structure; ranked fixes as `SourcePatch` lists; catalog pages | A failing machine-applicable fix is a compiler defect | ING-O-9 | 0 |
| `require` and outcomes | `CheckOutcome` per contract section 5; conditional `Pass`; protected sources; waivers | `Error(Failure)`; `Undecided { reason, needed }` | ING-O-8, ING-O-27 | 1 |
| Check independence | Adding or removing a check changes no other node's key | — | ING-O-27 | 1 |
| Free-text spans | Classified spans; handles for untrusted authors | `ING0003` | ING-O-32 | 1 |

## Execution

Until the code generator ships, the reference interpreter is the only Ingot executor on every target (contract section 7.4). Written in Rust, it interprets the IIR in the canonical class with `detmath` and no implicit FMA, checking non-finite values, fuel and depth after every step. Heap frames let a call suspend at an observation edge without stack switching, and one interpreter per worker holds every suspended call with its own allocator region, reserving memory as it is used.

| Measure | Target | Benchmark |
| --- | --- | --- |
| Interpreter time per GP1 feature body, operations cached | ≤ 200 µs on the reference laptop; ≤ 600 µs in browsers | `ingot-bench` on GP1 |
| Ingot share of a golden-product rebuild | ≤ 2%; above it, the code generator enters | GP1 and GP2 rebuilds with cached operations |
| Suspended feature calls | 500 concurrent calls within 256 MiB of the browser engine worker | Golden-product evaluations |
| Front-end re-check of an edited 2,000-line module | Under 30 ms | Edit-replay corpus |
| Drag residual program per frame, operations excluded | Under 1 ms | UIX drag scripts |
| Numeric Ingot against idiomatic Rust, once compiled | ≤ 2.5× natively; ≤ 4× in browsers | `ingot-bench` numeric programs |

All figures are targets. Heavy numeric loops go to operations or `#[ingot::feature]` Wasm components until the code generator exists.

**Decision D-ING-13:** The canonical-class reference interpreter is the only Ingot executor on every target until `ingot-bench` shows Ingot above 2% of a golden-product rebuild. Then a code generator to WebAssembly core modules enters, phase 2 at the earliest, running on Wasmtime with Cranelift natively and on each browser's engine; the interpreter stays for cold start, debugging, replay and differential testing. *Why:* phase 1's golden products need only orchestration speed, which an interpreter reaches, and a second executor would sit on the critical path with no gate need (R6-25). *Rejected:* the code generator in phase 1, the round 1 plan; native code from Cranelift (no browser path); compiling Ingot to Rust (a toolchain at run time); LLVM (slow to compile, no browser target). (revised in round 2)

When it enters, the code generator emits one module per compilation unit with a source map, cached in the CAS. Its modules pass the determinizer's verification (contract section 7.4), and ING-O-1 checks their fuel accuracy. Its optimizer never reassociates or contracts floating point, keeps every operation that can fail in program order, charges fuel computed on the canonical IIR, and never merges, duplicates or reorders Kiln calls.

Suspension lowers to resumable state machines, since Wasmtime's tier documentation lists stack switching as unsupported by Cranelift on aarch64. Each worker keeps one instance with per-call allocator regions, isolated by the compiler (no mutable globals) and the allocator. User modules replace the interpreter at the next feature call boundary, unobservably.

**Decision D-ING-14:** Plain values use reference counting with in-place update of uniquely referenced lists and records: Rust reference counts in the interpreter, Perceus in the code generator. *Why:* immutable, strict values form acyclic graphs, so reference counting needs no cycle collector; Perceus is "garbage free" with "guaranteed in-place updates"; prompt freeing keeps loops within the semantic memory limit, which allocator behavior never affects. *Rejected:* a tracing collector (pauses inside a drag frame); one arena per feature call (keeps garbage until the call ends); ownership types for users (ceremony). (revised in round 2)

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Reference interpreter | Canonical class; checks after every step; heap frames; memory reserved as used | Abort `ResourceExhausted` from the host | ING-O-1, ING-O-33, ING-O-34 | 0 |
| Code generator | Deterministic Wasm subset; verified by the determinizer; state machines; Perceus | Verification rejection is a compiler defect | ING-O-1, ING-O-14 | 2 at the earliest |

## Rust features and Wasm components

Contract section 4 lets features be written in Rust as Wasm components, and ECO's tier rule (D-ECO-6) decides when. `#[ingot::feature]` writes the WIT world, the `wit-bindgen` glue and a typed Ingot wrapper, and a build fails if a checked-in artifact differs from its regeneration.

```rust
/// Involute spur gear tooth profile, closed, centered on the origin.
#[ingot::feature(package = "acme::gears", category = "Power transmission", icon = "gear")]
pub fn involute_profile(
    #[ingot(range = "0.1mm..=50mm")] module: Length,
    #[ingot(range = "6..=400")] teeth: u32,
    #[ingot(default = "20deg", range = "14.5deg..=30deg")] pressure_angle: Angle,
    ctx: &mut OpCx,                                                   // supplied by the host
) -> Result<Body, GearError> {
    let mut s = ctx.planar_builder(Plane::XY, ctx.site("profile")); // explicit, stable call key
    for i in 0..teeth {
        s.add_spline(ctx.site_keyed("flank", i), &flank_points(module, pressure_angle, i)?)?;
    }
    s.finish_region().map_err(GearError::from)
}
```

The SDK's quantity types come from the prelude's kind table, so dimensions survive in Rust and the macro checks each parameter against its WIT alias. `ingot-bindgen` emits `GearError` as an Ingot enum implementing `Error`, with the codes and fix templates declared in Rust.

| Rule | Mechanism |
| --- | --- |
| A Wasm component call is an Op keyed by the determinized binary's SHA-256, the export and the arguments (contract section 7.2) | Pinned in `ingot.lock` (ECO) |
| Evaluation worlds import no WASI; randomness arrives only as a `seed: u64` argument from an `Rng` | Contract section 7.4 |
| Operation calls go through `crucible:ops/anvil` and `crucible:ops/flux`, served by Kiln as recorded Op dependencies | No second path to the engine |
| Every operation call and created entity takes a call key appended to the call's `OpSite`; duplicates fail with `ING8201` | Stable `EntityId`s |
| Fuel is metered by the determinizer and limited by the wrapper's `fuel:` within the manifest maximum | Deterministic limits |
| Traps and fuel or stack exhaustion are cached `Failure`s; host resource loss is an Abort | Contract section 7.2 |
| Results with error estimates map to `Approx` values or `ErrorBudget` parts; `outside-envelope` maps to the validity flag | Wrapper convention |
| Diagnostics written through `crucible:host/diagnostics` attach to the call's span in emission order; Wasm component strings become `ExternalText` | Write-only accumulator |
| The wrapper is the public interface, and the raw `extern fn` is `pub(package)` | One typed signature for dialogs and semantic versions |

| WIT | Ingot |
| --- | --- |
| `bool`, `s8` to `s64`, `u8` to `u32`; `u64` | `Bool`, `Int`; `u64` fails with `ING6101` above 2⁶³ − 1 |
| A `u64` named `seed`; ECO's `fidelity` enum | `Seed`; omitted, filled by the host, because code cannot observe fidelity |
| `f32`, `f64`; `crucible:units` aliases | `Real`; `Length`, `Force`, `Temperature` (kelvin, converted in the wrapper) |
| `string`, `list`, `option`, `result`, `tuple` | `ExternalText` for Wasm component strings; `[T]`, `Option`, `Result`, tuples |
| `record`, `variant`, `enum`, `flags` | `record`, `enum`, `enum`, `Set<Enum>` |
| Body and Field resources; other resources | `Body`, `Field<D, V>` handles; opaque handles owned by the wrapper |

A bare `f64` parameter becomes `Real` with `ING8101`, asking for a unit alias in `ingot-bindgen.toml`. A Rust feature is an opaque debugger frame with its inputs, outputs and nested operations, and has a forward derivative only when `#[ingot::feature(tangent = …)]` names an exported tangent.

**Decision D-ING-15:** The fallback is an attribute macro, `#[ingot::feature]`, generating the WIT world, the `wit-bindgen` glue and a typed Ingot wrapper from one Rust signature. The wrapper is the feature's only public face, and operation calls go through the WIT package `crucible:ops`. *Why:* one signature carries units and ranges to the type checker and dialogs, so a Rust feature looks like an Ingot one. *Rejected:* hand-written WIT and wrappers (three signatures that drift); native Rust plugins (unsafe, impossible in browsers); `crucible:geom/ops`, the round 1 interface. (revised in round 2)

A package feature calling a Wasm component through its generated binding:

```
//! Gray-body radiation exchange inside a closed, diffuse enclosure.
use package::generated::solver::{solve_raw, SolveRequest}      // from crucible:physics/solver@1

#[feature(category: "Thermal", icon: "radiation")]
pub feature radiation_exchange(
    enclosure: Body, hot: Query<Face>, cold: Query<Face>,
    emissivity: Real in 0.01..=1.0 = 0.85,
    t_hot: Temperature = 80degC, t_cold: Temperature = 20degC,
    seed: Seed = Seed::from(enclosure),                         // hashes the GeometryId, not names
) -> Field<Body, HeatFlux> {
    let temps = Field::per_entity(enclosure, [hot => t_hot, cold => t_cold])
    let out = solve_raw([enclosure], [temps], SolveRequest {
        parameters: [("emissivity", emissivity)], tolerance: 0.005,
        seed: Rng::new(seed).split("radiation").seed(),
    })?
    let flux: Field<Body, HeatFlux> = out.field("net_flux")?    // checks the recorded dimension (ING8102)
    flux.require(out.scalar("reciprocity_error")? < 1e-3, name: "reciprocity", severity: Warning)
}
```

The Wasm component's error estimate becomes the statistical part of the Field's `ErrorBudget`, `Guaranteed` only if it declares one. The package test compares two concentric spheres with the closed form Q = A₁σ(T₁⁴ − T₂⁴) / (1/ε₁ + (A₁/A₂)(1/ε₂ − 1)).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `#[ingot::feature]` | One Rust signature generates WIT, glue and wrapper | Artifact drift fails the build; `ING8xxx` | ING-O-17 | 1 |
| Wasm component calls | Ops keyed per contract section 7.2; `crucible:ops`; call keys; determinizer fuel | `ING8201`; typed `Failure`s; Aborts | ING-O-1, ING-O-17 | 1 |
| Binding generation | WIT to Ingot with units | `ING8101`, `ING8102` | ING-O-17 | 1 |

## Packages and versions

A package is a directory with `ingot.toml` and modules under `src/`, rooted at `src/lib.ingot`; a design repository's root is `src/main.ingot`, whose `pub` items are its outputs. Items are private to their module, visible package-wide with `pub(package)`, or public with `pub` and part of the semantic-version interface. A `use` path starts with a dependency, `package`, `self` or `super`.

Imports are acyclic (`ING1301`), as in KCL, and two globs supplying one name make it ambiguous (`ING1201`).

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

At publish the registry diffs the public interface and refuses a minor or patch release that breaks it (ECO). Ingot defines "breaks":

| Change | Release |
| --- | --- |
| Remove or rename a public item, parameter, field, role or coordinate system; change a parameter's dimension, kind or type; add a parameter without a default; narrow a range; add a variant to an exhaustive enum | Major |
| Change a default value, or the entity names a public feature produces on the package's test designs | Minor, labelled output-changing (D-ECO-14) |
| Add a defaulted parameter, an item, a role or a variant to a `#[non_exhaustive]` enum; widen a range | Minor |
| Change only documentation, metadata or private code that leaves test-design outputs and names unchanged | Patch |

`ingot.lock` is sorted TOML written only by tools. ING owns `[language]`, the language behavior version fixing evaluation semantics, the cost table, the n-ary lowering rule and std numerics. `[operations]` pins operation versions (KLN and the owners), and `[[package]]`, `[[asset]]` and `[[external]]` pin the rest by SHA-256 (ECO); compiler releases may change diagnostics and speed, never values, failures or fuel.

**Decision D-ING-16:** The lockfile pins a language behavior version beside the operation versions, and a toolchain implements every language behavior version in its support window. *Why:* an old design must rebuild identically, and fuel costs and std numerics are part of its result. *Rejected:* pinning the toolchain release (old toolchains kept runnable forever); letting editions carry behavior (ECO's D-ECO-23 forbids it).

Resolution uses PubGrub, which can "explain errors more clearly than the alternatives": `ING7001` carries its derivation and relaxations as fixes. Two major versions of a package may coexist; passing a value between them fails with `ING7201`.

Editions follow Rust's model and D-ECO-23: they change surface syntax, the prelude and lint defaults, never behavior, and all lower to one IIR. `crucible migrate` applies machine-applicable fixes on the lossless tree and rejects any item whose IIR changes beyond spans; test designs must then build to identical output hashes. Rust's guide notes that "Cargo's automatic migrations aren't perfect", and the IIR check makes Ingot's exact.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Modules and visibility | Three levels; acyclic imports | `ING12xx`, `ING1301` | ING-O-5 | 1 |
| Semantic-version rules | The table above, including entity-name changes | Publish refused (ECO) | ING-O-18 | 1 |
| Lockfile and behavior versions | `[language]` pinned; compiler releases never change values | A changed value is a defect | ING-O-1, ING-O-18 | 1 |
| Resolution | PubGrub with explanations; two majors coexist | `ING7001`, `ING7201` | ING-O-18 | 1 |
| Editions and migrations | IIR-preserving rewrites only | Non-preserving rewrites listed, not applied | ING-O-19 | 2 |

## Feature metadata and dialogs

A feature's signature generates its dialog, its documentation page and its agent tool schema; attributes refine them.

| Source element | Generated UI |
| --- | --- |
| Quantity parameter | Numeric field with unit, accepting expressions (UIX) |
| `Tol<T>` parameter, or a `T` with a toleranced default | Value field with a tolerance sub-field: symmetric, deviations, limits or fit code |
| `Bool`; `enum` | Toggle; segmented control up to five variants, else a dropdown |
| `Query<K>` | Selection field with the readable query and a filter from `K` |
| `Material`, catalog part types | Pickers bound to the material library and the catalog |
| `Option<T>`, record, `[T]` | Enable toggle; group; list editor |
| `in` range; doc comment | Field and slider bounds checked at evaluation (`ING6501`); help text |

| Attribute | Meaning |
| --- | --- |
| `#[feature(category:, icon:, handles:)]` | Toolbox placement, icon, manipulator handles (UIX handle kinds) |
| `#[ui(group:, advanced, visible_if:, step:, filter:, label:)]` | Grouping, progressive disclosure, conditional visibility, slider step, selection filter, label |
| `#[roles(…)]`, `#[fuel(…)]`, `#[example]` | Created roles; a raised fuel limit; a compiled, evaluated doc example |
| `#[deprecated(since:, instead:)]`, `#[removed(in:, instead:)]` | Lifecycle with fixes |

`visible_if` takes a pure closure over the parameter record, checked on default values and evaluated by the interpreter as values change. FeatureScript expresses the same with `if` statements in a `precondition` block, where each parameter may appear only once.

**Decision D-ING-17:** Dialogs are generated from feature signatures, types, doc comments and a small attribute vocabulary, with conditional visibility as pure closures; there is no dialog language. *Why:* one declaration serves the dialog, docs, semantic-version checks and agent tool schemas, so they cannot drift; Onshape's preconditions show generated dialogs work at scale. *Rejected:* FeatureScript-style precondition blocks (a second statement language for UI); hand-built dialog descriptions (drift).

`crucible doc` generates reference pages; every `///` code block compiles, and `#[example]` blocks evaluate in CI with their checks. A public item without a doc comment fails the registry's coverage gate (ECO), and AGT's tool schemas read the same data.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Dialogs from signatures | Types and attributes to fields, groups, handles and visibility | `ING6501` out of range | ING-O-20 | 1 |
| Documentation | Compiled and evaluated examples; coverage gate | Publish refused (ECO) | ING-O-20 | 1 |

## Tooling

### Lossless tree and blocks

`ingot-syntax` parses into a lossless green-red tree in rust-analyzer's design, keeping whitespace and comments, with the `rowan` crate (MIT or Apache-2.0). Every byte belongs to exactly one block, as Kiln's live document requires.

| Block | Head | Children |
| --- | --- | --- |
| File; item | Inner attributes; attributes, docs and signature | Items; members, with the closing brace as tail |
| Parameter, field, variant; table row | The whole text | None |
| Statement; arm | Text up to the first nested block; the arm's opener | Arms; statements, with the closer as tail |

Comments belong to the block that follows them, and order-insensitive lists (`use` lists, named arguments, record fields) merge as sets. Parsing is block-local: each block parses as head, arm holes and tail under its own production, and an error stays inside its block as `ERROR` nodes. A block that stops parsing after a concurrent edit therefore keeps its kind and position, and "the last good result for that block" is well defined.

**Decision D-ING-18:** The grammar is designed for structural editing: newline-terminated statements, one statement per block, comments owned by the following block, named arguments that merge as sets, atomic literals, and block-local parsing. *Why:* the live document needs a block for every unit of concurrent work and an owner for every byte, and file-level recovery re-associated blocks after a malformed one (R3-32). *Rejected:* a projectional editor (review, diff tools and agents work on text); free layout with semicolons (two layouts, two diffs); file-level error recovery. (revised in round 2)

### Formatting and structural edits

`crucible fmt` produces one idempotent layout per block: 100 columns, 4-space indents, one argument per line when a call breaks, one pipeline stage per line, alignment only in tables. Every GUI action and agent edit becomes the smallest `SourcePatch` list the formatter leaves unchanged:

| Action | Minimal source edit |
| --- | --- |
| Change a dialog value; drag a dimension | Replace one literal token, keeping its unit; drags replace the literal UIX's edit plan chose |
| Add a feature | Insert one statement after the anchor, binding a fresh name derived from the feature (`fillet_2`) |
| Delete or reorder a feature | Remove or move one statement block with its comments, refused with the reason if a binding would precede its definition |
| Suppress; set a tolerance | Toggle `#[suppressed]`; rewrite `4mm` to `4mm ± 0.1mm` |
| Rename a binding | Rename every use and add `#[was(old_name)]`, keeping entity names |
| Add a check | Insert a `require` statement, or attach `.require(…)` to a single-expression body |

### Language service and tools

The language service implements LSP 3.17 semantics in `ingot-service`. The UI and agents reach it through `api`, and it also runs as an LSP server over stdio with first-party VS Code and Zed extensions. A custom request, `crucible/reveal`, drives Crucible's viewport from those editors for cross-probing; the in-app code panel covers editing, diagnostics, hover, completion and scrubbing (UIX).

It offers pull diagnostics with evaluation failures, semantic tokens for units and roles, hover with values, bounds and tolerance limits, and inlay hints for dimensions and scalar flavors. Completion knows units, roles and parameters; every fix is a code action; and a source map links each `EntityId` to its creating `OpSite` and span. Targets: completion and hover within 50 ms, diagnostics for an edited 2,000-line module within 100 ms.

**Decision D-ING-25:** In phase 1 the language service ships inside Crucible and as an LSP server over stdio with first-party VS Code and Zed extensions, plus a request that drives Crucible's viewport. *Why:* code-CAD users already work in those editors, and an in-app editor alone would have to compete with them as a product (R6-23). *Rejected:* the in-app code panel as the only editor; external editors without viewport cross-probing.

| Tool | Behavior | Phase |
| --- | --- | --- |
| Debugger | Runs a feature call in the interpreter reading every operation result from the cache, so stepping never recomputes geometry; Debug Adapter Protocol with `stepBack` and `reverseContinue`, exact because evaluation is pure; intermediate Bodies colored by creating `OpSite`; queries evaluated against the current frame | 2 |
| REPL and notebooks | Cells compile as modules importing earlier cells' names; saved as `.ingot` files with `//% cell` markers; outputs are Kiln values, never saved in the file | 2 |
| Tests | `#[test]`, `#[test(golden)]` comparing `ObjectId`s, `#[test(property, cases:)]` drawing seeded parameters; `assert_close` passes only on enclosures, `assert_checks_pass` fails on `Undecided`; failures shrink to a reproducible call | 1 |
| Benchmarks | `#[bench]` reports deterministic fuel and wall time; CI tracks fuel exactly and time statistically; `ops: cached` or `ops: cold` | 1 |

Tests are deterministic, so a flaky test is an engine defect; tests under `oracles/` are protected.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Lossless tree and block-local parsing | Every byte in one block; errors stay inside their block | `ERROR` nodes; never a crash | ING-O-2, ING-O-29 | 0 |
| Formatter and structural edits | Canonical, minimal, comment- and name-preserving | Refused edits explain why | ING-O-10 | 1 |
| Language service | LSP 3.17 in-app and over stdio; VS Code and Zed extensions; viewport request | Degrades to plain text editing (UIX) | ING-O-21 | 1 |
| Debugger | Replay from cache; reverse stepping | — | ING-O-22 | 2 |
| REPL and notebooks | Cells as modules; outputs from Kiln | — | ING-O-5 | 2 |
| Tests and benchmarks | Geometric assertions; golden and property tests; fuel tracking | Deterministic failures | ING-O-1, ING-O-33 | 1 |
| KCL importer | KCL programs to Ingot with explicit units (D-ING-19) | Unmapped constructs listed | ING-O-36 | 3 |

## State of the art

| Aspect | Zoo KCL | Onshape FeatureScript | CadQuery, build123d | OpenSCAD | Ingot |
| --- | --- | --- | --- | --- | --- |
| Host | Own language; Rust, MIT | Own language inside Onshape | Python libraries on OpenCascade | Own language; CGAL a build prerequisite | Own language; Rust |
| Typing | Numeric types with units; bare numbers take the file default | Dynamic, with `ValueWithUnits` | Dynamic Python, type hints in build123d | Dynamic; `undef` | Static; inferred bodies, required signatures |
| Units | Lengths, angles, counts; "KCL doesn't support area, volume, or other higher-dimension units" | Dimensional analysis; mixing units throws | None | None | Rational dimension algebra, kinds, affine temperatures, at compile time |
| Tolerances | None | None in the language | None | None | `Tol<T>` with affine worst case, explicit statistics, typed GD&T |
| Entity selection | Tags on sketch segments [unverified: tag syntax] | `qCreatedBy(id + …)` over feature ids | String selectors (`">Z"`); build123d sorting, `Select.NEW` | None [unverified] | Provenance and role queries, anchored ranks, no positional access |
| Composition | Pipelines with `\|>` | `context`, `id` and definition maps | Fluent chains; builder contexts | CSG modules | Pipelines, methods, builder blocks |
| Purity | Mostly functional | No external input, time or randomness | Python: anything | Functional; last assignment wins | Pure, fuel-bounded, explicit keyed randomness |
| UI generation | Sketches in function bodies not editable by point-and-click | Precondition annotations | None | Customizer comments [unverified] | Signatures and attributes |
| Versioning | `kclVersion` per program | std imported by pinned version string | Python packaging | Releases | Editions; lockfile pins of language and operation behavior |
| Execution | Commands to Zoo's hosted engine, view streamed back as video | Onshape's cloud [unverified] | Local Python | Local | Local on every Tier 1 target and in the browser |

KCL's documentation gives `10in * 25.4` as `254in`, and FeatureScript threads `context` and `id` through every call; Ingot's types and dataflow remove both.

**Decision D-ING-19:** Crucible builds Ingot's implementation from scratch and does not fork KCL's MIT-licensed implementation; it studies KCL's tests and documentation as references, with attribution. *Why:* most of what matters here is new, from rational dimensions and `Tol` to text-derived sites. `kcl-lib` also couples execution to an engine connection, which cloning its `ExecutorContext` shares, per its API documentation. *Rejected:* forking `kcl-lib` (we would replace most of it and inherit default units); KCL source compatibility (its unit semantics conflict with principle 5). A KCL importer mapping default units explicitly is phase 3 work in `io/`.

Figures are targets on contract section 13.3's reference laptop.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Units and dimensions | Units-of-measure inference (F#); kinds and affine points (mp-units, after ISO 80000) | F# units of measure; mp-units; Pint at run time | Rational dimensions, kinds, strong angular system, affine temperatures, erased at run time | ING-O-4; check time under 5% of front-end time |
| Tolerance arithmetic | Affine arithmetic (Comba and Stolfi; de Figueiredo and Stolfi); GUM and Supplement 1 | Spreadsheet and 1D stack tools [unverified] | Affine forms per site and realizing Part; explicit RSS and Monte Carlo | ING-O-7 |
| Approximate comparisons | Interval enclosures with three-valued logic | FLX's budgets | One decision rule over `ErrorBudget`s with conditional passes | ING-O-8 |
| Entity naming | Provenance with history (build123d's `Select.NEW`; FeatureScript's `qCreatedBy`) | Onshape FeatureScript | Text-derived `OpSite`s, keyed iteration, anchored queries over Anvil lineage | ING-O-25, ING-O-26, ANV-O-NAME-2 |
| Incremental compilation | Red-green memoization with early cutoff (Salsa) | rust-analyzer | Salsa-style stages inside Kiln; split node outputs | ING-O-13; re-check under 30 ms |
| Execution | Compiled code "an order of magnitude faster than interpretation" (Xu and Kjolstad); Cranelift within about 14% of LLVM; browsers 45% to 55% slower than native on SPEC (Jangda and colleagues) | V8, Wasmtime; wasmi for interpreted Wasm with fuel | Interpreter now; Wasm code generator when justified | ING-O-33; ≤ 2.5× Rust natively, ≤ 4× in browsers once compiled |
| Memory in pure languages | Perceus reference counting with reuse (PLDI 2021) | Koka | Reference counting with in-place update; Perceus in the code generator | ING-O-34 |
| Deterministic execution | Wasm with fuel and canonical semantics (Wasmtime guide; Wasm 3.0 deterministic profile) | Wasmtime with NaN canonicalization | One canonical interpreter; verified generated modules | ING-O-1 |
| Live programming | Typed holes with evaluation around them (Hazel) | Hazel | Holes from the error-resilient parser | ING-O-15 |
| Bidirectional editing | Program repair from output edits (Sketch-n-Sketch) | Sketch-n-Sketch; Onshape dimension editing | Provenance ranking, then derivatives | UIX's intent-match rate |
| Lossless syntax trees | Red-green trees (Swift libsyntax, rust-analyzer) | rust-analyzer with `rowan` | `rowan`, block grammar, block-local parsing for Loro's movable tree | ING-O-2, ING-O-29; reparse of 2,000 lines under 5 ms |
| Version resolution | PubGrub | uv | PubGrub through ECO's resolver | ING-O-18 |
| Language evolution | Editions with automated migration (Rust) | Cargo | Editions plus an IIR-equality check | ING-O-19 |
| Dialogs from code | FeatureScript preconditions | Onshape | Typed signatures plus attributes | ING-O-20 |
| Sketch language | Constraint graphs catalogued by SketchGraphs | Onshape's sketcher [unverified: SketchGraphs source system] | Builder blocks of symbolic entities and `Equation` items | ING-O-23 |
| Debugging | DAP with `stepBack` and `reverseContinue` | Record-and-replay debuggers [unverified] | Replay from Kiln's cache, exact because evaluation is pure | ING-O-22 |

## Platform notes

| Platform | Note |
| --- | --- |
| Every target | The interpreter is one Rust implementation in the canonical class, so a divergence is a platform defect that ING-O-1 finds |
| Browsers | The interpreter, compiled to wasm32, runs in the engine worker and yields at Kiln calls in single-threaded builds; evaluations above 512 MiB move to the heavy worker or go remote (PLT's browser memory table) |
| iPadOS (Tier 2) | Ingot needs no JIT: the interpreter runs natively or in the web build inside WebKit, whichever contract section 7.4's path uses; Wasm components follow that section |
| Tier 1 preview targets | Same build; ING-O-1 and the golden products run headless |
| Code generator (phase 2 at the earliest) | Core Wasm with fixed-width 128-bit SIMD only; browser pages allow `'wasm-unsafe-eval'`, without which "WebAssembly is blocked" (MDN); the macOS JIT entitlement is PLT's |
| Floating point | Correctly rounded basic operations and `detmath` only; no FMA, flush-to-zero or excess precision |
| Text | Repository-relative `/` paths, NFC and LF, normalized on load (PLT) |
| Air-gapped installs | Compiler and interpreter ship in every build; no network is needed |
| Accessibility | Diagnostics are plain text with spans; the code panel is UIX's |
| Tier 3 | Interpreter results stay out of shared caches until the determinism suite passes |

## Interfaces with other subsystems

### Ingot provides

| To | Provides | Types |
| --- | --- | --- |
| KLN | Front-end stages; module code hashes; split node outputs; call protocol with program order; literal overrides; limits in keys; text-derived sites; block grammar with block-local parsing; free-text span classes; variant regions for the 150% BOM | `OpSite`, `Feature`, `Check` |
| ANV | `OpSite`s; `QueryPlan`s with anchored ranks; named sub-entities of sketch helpers; data-flow copy marks; `InputSensitivity`; the `Truth` rule for filters; GD&T attributes | `Query`, `Tol<T>` |
| FLX | Product- and parameter-domain `Field` types; `Complex<Q>`, `im`, `.absolute()`, `select`; `Expr<T, Out>` and record results; `Approx`, `Truth` and the decision rule; `goals:` and `wrt:` as ordinary arguments | `Field<D, V>`, `Expr<T>`, `Approx<T>` |
| MEC | Features, builder blocks, symbolic constraints, families, roles, `Tol<T>` with fits, typed aspects, keyed iteration and `skip:` keys, `#[interface]` | `Feature`, `Tol<T>`, `Query` |
| ELX | `network { … }` with set-like accumulation; port power expressions checked by the type checker; `Tol` correlation groups; `CatalogSelection` re-resolution; `#[configuration]` | `Tol<T>`, `Network` |
| COV, MFG | Records, enums, `Map`, `Range` as interval, `Decimal` and `Money<C>`, `require`, kinds for parameter domains | `Quantity<D>`, `Check` |
| UIX | Language service; `EntityId`-to-span map; dialog metadata and handles; phase 1 edit-plan ranking; minimal `SourcePatch`es; `crucible/reveal` | `SourceSpan`, `Feature` |
| AGT | Diagnostics with fixes; the formatter; metadata for tool schemas; `ExternalText`; free-text span classes; `CheckOutcome` values | `Check`, `Feature` |
| ECO | Manifest language keys; lockfile `[language]`; modules and editions; semantic-version rules; binding conventions | `Feature` |
| PLT | The interpreter on every target; verified generated modules from phase 2 at the earliest | `PlatformClass` |

### Ingot requires

| From | Requirement |
| --- | --- |
| KLN | Suspending scheduler; keys with `OpSite`, code hashes and limits; split outputs with their own change markers; Aborts; demand-depth and fuel limits; `Differentiable` and reverse traversal; span integrity in `repo`; block ids mapped onto text identities |
| ANV | `anvil::resolve` with notes, `RankSwap` and compiling fixes; role vocabularies with per-parameter surface or extent use; copy and mirror roles; split policy `Fail` for GD&T; certified sketch solves; canonical geometric order; `shape_velocity` from phase 2 |
| FLX | Regularized reductions with `ErrorBudget`s; calibrated `Estimated` bounds; singular sets; tangent and adjoint rules; `away_from` regions |
| PLT | `detmath` for native and wasm32; the determinizer and `wasm-host`; text normalization; the browser memory table |
| ECO | Registry, signing, publish-time interface diff, Wasm component bundles, the RFC process |
| MEC | GD&T records and validators per dialect; std features with roles and keyed generators; `std::mech::refgeom` |
| AGT | `SourcePatch` application; `read.*` and `inspect.describe` returning free-text handles |

## Oracles

All oracles live under `oracles/ingot/` (protected). The corpus is std, the golden products, every registry package's tests and a generated set of random well-typed programs.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| ING-O-1 | Conformance: the interpreter on every Tier 1 target and browser engine, and compiled code once it exists, on values, failures, fuel and Kiln call sequences | Bit-identical on the corpus |
| ING-O-2 | Parse then print, for valid and invalid inputs | Every byte reproduced |
| ING-O-3 | Parser fuzzing on arbitrary bytes | No crash, hang or unbounded memory in 10⁹ executions per release |
| ING-O-4 | Units: a seeded-error corpus of dimension, kind, affine, degree-radian and rpm-hertz mistakes; at least 50 textbook rotational, electrical and thermal formulas | Every seeded error rejected with its code; every formula type-checks without casts |
| ING-O-5 | Typing judgments on a curated corpus; random well-typed programs | Expected judgments; zero internal type failures |
| ING-O-6 | Deepest legal recursion on every target, and one deeper | Runs everywhere; fails with `ING6302` everywhere |
| ING-O-7 | Tolerances against exact rational stacks and 10⁶ samples per nonlinear case; Part-keyed symbols | Exact for linear stacks; containment for nonlinear; spacers from one specification vary independently |
| ING-O-8 | Comparisons with injected bounds and kinds | Never `True` or `False` against the exact relation; `Indicator` and unquantified parts never decide; `conditional_on` lists exactly the unquantified sources |
| ING-O-9 | Machine-applicable fixes in the corpus | 100% compile and remove their diagnostic |
| ING-O-10 | Recorded GUI sessions | Minimal patches; every comment kept; every `OpSite` outside the touched statements kept |
| ING-O-11 | Query lowering | Equal queries hash equal; unanchored rank selectors raise `ING-L-FragileSelector`; `Tol` filter arguments fail |
| ING-O-12 | Drag specialization on golden-product drag scripts | Residual and full programs bit-identical |
| ING-O-13 | Minimal re-evaluation over 500 scripted edits, fuel-only edits included (shared with Kiln's minimality oracle) | Re-executed nodes equal the reference set; none after fuel-only edits |
| ING-O-14 | Differential fuzzing of the code generator: interpreter against compiled code, optimized against unoptimized | No divergence per release |
| ING-O-15 | Programs with random holes | Hole-independent bindings equal the complete program's |
| ING-O-16 | Derivatives on smooth programs; dependence sets; phase 1 ranking on drag scripts | Taylor order 2 ± 0.1; dependence exact; provenance literal ranked first |
| ING-O-17 | `#[ingot::feature]` and bindings | Checked-in WIT and wrappers match regenerated ones; units match WIT aliases |
| ING-O-18 | Unsatisfiable dependency fixtures; two-major coexistence | Every failure explained; no silent choice |
| ING-O-19 | Edition migrations on the corpus | IIR and output hashes preserved |
| ING-O-20 | Metadata and examples | Every std feature has a dialog, docs and an evaluated example; this tab's examples compile and evaluate |
| ING-O-21 | Service latency on an edit-replay corpus, in-app and over stdio | Within the stated targets at p95 |
| ING-O-22 | Debugger replay | Forward then backward steps give identical frames; replay reports the original failure span |
| ING-O-23 | A fixed SketchGraphs sample converted to sketch blocks | Every constraint type expressible; at least 99% re-solve within tolerance (target) |
| ING-O-24 | `f(n) = f(n + 1)` on every Tier 1 target | Aborts with `DemandDepthExhausted`; no memo entry |
| ING-O-25 | Golden products exported to Git, re-imported and rebuilt; appended, wrapped and inserted calls of other names; renames with `#[was]` | Every `OpSite` and `EntityId` of untouched calls unchanged |
| ING-O-26 | One element inserted into or removed from geometry-driven patterns and query loops | Only that element's entities renamed |
| ING-O-27 | Adding or removing any `require` | Every non-check node key unchanged |
| ING-O-28 | Evaluations under varied organization ceilings | Same limit outcome for the same source and manifest; a lower ceiling aborts at admission and writes nothing |
| ING-O-29 | Block-local parsing | Parsing the concatenated blocks reproduces the tree when every block parses; a failing block keeps its kind and position |
| ING-O-30 | Variant regions | Instances under computed conditions rejected with `ING2601`; the 150% BOM equals enumeration on small fixtures |
| ING-O-31 | Contract section 6's example | Compiles; evaluates with the stated outcome kinds; `width + load` gives `ING3001` |
| ING-O-32 | Free-text spans on a labelled corpus; hidden characters | Classification matches; every hidden character rejected with `ING0003` |
| ING-O-33 | Interpreter speed | Within the stated per-feature targets; Ingot share of golden-product rebuilds reported |
| ING-O-34 | 500 concurrently suspended golden-product feature calls in a browser engine worker | Within the stated memory target |
| ING-O-35 | Branches on `Undecided` across fidelities | `Pending` below the ceiling, decided at the next fidelity; `ING6401` at the ceiling; releases evaluate every node at `SignOff` |
| ING-O-36 | KCL sample programs through the importer | Each builds the reference geometry within tolerance or lists its unmapped constructs |

## Phasing

| Phase | Ingot contribution to the gate |
| --- | --- |
| 0 | "Unit errors fail to compile" is ING-O-4; the interpreter, fuel and Kiln protocol join the determinism suite (ING-O-1, ING-O-6); parser, types and interpreter by month 6 and text-derived `OpSite`s for Anvil's `EntityId` (ING-O-25), per contract section 13.2 |
| 1 | GP1 and GP2 build from std Ingot on the interpreter: tolerances forwarded to PMI, `Approx`, the decision rule and checks, queries, sketches, GD&T, families, variant regions, packages and lockfile, dialogs, the language service in-app and over stdio, tests; interpreter targets met (ING-O-33). Deferred per contract section 13.2: the code generator, Perceus and the state-machine transform |
| 2 | GP3 and GP4: assemblies with variants at scale; the code generator if `ingot-bench` shows Ingot above 2% (ING-O-14); debugger and notebooks; reverse-mode derivatives and derivative-ranked edit plans; the first edition migration |
| 3 | GP5: ELX data modules and `network { … }` at scale; KCL importer (ING-O-36) |
| 4 | GP6: large symbolic forms and parameter-domain forms in use (FLX) |
| 5 and later | Proposed: a mechanized soundness proof of the dimension and tolerance calculus, and a second interpreter for aerospace and medical certification |

## Open questions

1. **Kind granularity.** std starts with the kind pairs in "Dimensions" and adds kinds only on evidence from user errors.
2. **Frequency into phase.** Trigonometric functions accept a dimensionless phase, so `sin(f * t)` with `f` in hertz compiles without the 2π. A lint on a `Frequency` factor reaching a phase is proposed.
3. **Instances at geometry-driven positions.** Static Instance existence (D-ING-22) forbids a fastener per hole of a resolved query. Proposal: the count comes from a configuration parameter and a check compares it with the resolved holes; MEC confirms.
4. **Affine arithmetic at scale.** Stacks over 10⁵ sites may need symbol condensation; phase 2 measures the threshold and how to report it.
5. **ELX data modules.** Layouts of 10⁶ items may parse too slowly as Ingot; the fallback is a binary sidecar keyed by statement identity.
6. **`Decimal` resolution.** Is 10⁻⁹ enough for every currency and pricing rule MFG needs?
7. **Default distributions.** MFG may prefer process-specific defaults, which make results depend on the process profile.
8. **Feature granularity.** Which std helpers are `fn` and which `feature`; MEC, FLX and ELX review the split before phase 1 freezes std.
9. **Jacobian types.** `Mat<R, C>` error messages need design with FLX.
10. **Literal sites under live edits.** A concurrent rename of a binding during a drag loses the override's site and ends the drag with a notice; UIX confirms.
11. **Findings declined in part.**
    - R2-06: calls get no CRDT identity, because contract section 5 derives call identity from name and occurrence; inserting a same-name call renames later same-name calls in its statement.
    - R3-33: one instance per worker with state machines applies to the code generator; the interpreter reaches the same isolation with heap frames.
    - R6-33: ING sets only its own ratios; Wasm component and user-form ratios belong to PLT, ECO and FLX.
    - R3-47: Ingot runs on the interpreter on iPadOS, so the Pulley fallback concerns Wasm components only (contract section 7.4).
    - R2-18: ING adds the dialect modules and the split policy; the extended GD&T record is MEC's.

## Contract change requests

- **CCR-ING-11. Pending branches.** Contract section 5's `Truth` says `if` on `Undecided` "fails loudly"; add "at the Evaluation's fidelity ceiling; below it the node's status is `Pending` until the next fidelity decides". *Reason:* R3-14; otherwise every branch on a Flux result fails at `Interactive`.
- **CCR-ING-12. Rotation and phase.** Add to contract section 5's `Quantity<D>`: oscillation angular frequency is a kind of T⁻¹ and phase is dimensionless; a rotation becomes a phase only through `radian`. *Reason:* with angular frequency in rad/s, ω = √(k/m) and the reactance ωL are ill-typed, and the 50-formula oracle needs them.
- **CCR-ING-13. `OpSite` as a frame path.** Contract section 5 defines statement and call identity; add that an `OpSite` is the path of frames (statement, call, keys) from the Evaluation's root, `fn` calls included. *Reason:* two calls of one helper must name their entities apart (R3-05).

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
25. ASME, Y14.5.1-2019: https://www.asme.org/codes-standards/find-codes-standards/y14-5-1m-mathematical-definition-dimensioning-tolerancing-principles/2019
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
