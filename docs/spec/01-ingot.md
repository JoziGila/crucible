# Ingot design language (ING)

Ingot is Crucible's design language: pure, strict and statically typed, with units, dimensions, tolerances, approximation error and geometric references as types, so unit and dimension errors never reach evaluation. Features compile through a typed dataflow IR into WebAssembly that runs identically on every Tier 1 target, while every operation call becomes a node in Kiln's memoized graph. The visual editor, the code editor and agents all edit one lossless syntax tree, so each edit is a minimal, comment-preserving, mergeable source change.

## Scope and principles

### What this tab owns

| ING owns | ING does not own |
| --- | --- |
| Lexical syntax, grammar, canonical formatting, editions | Operation semantics and behavior versions (Anvil, Flux) |
| The type system: `Quantity<D>`, `Tol<T>`, `Approx<T>`, `Truth`, records, enums, traits, generics | Query resolution against lineage (Anvil D-ANV-15); Ingot lowers queries to plans |
| Evaluation semantics, purity, determinism at the language level, fuel | Scheduling, caching, storage and the determinism policy per operation (Kiln) |
| Lowering to the dataflow IR and the incremental contract with Kiln | The kernel IR and its CPU and GPU emitters (Flux) |
| Compilation to WebAssembly, the reference interpreter, Ingot's memory model | The Wasm component runtime and its instrumentation pass (Platform tab, D-PLT-22) |
| The error model: failures, diagnostics, fix-its, `require` and check outcomes | Feature semantics of `std::mech`, `std::flux` and other std packages (MEC, FLX, COV, MFG, ELX) |
| Modules, packages, visibility, lockfile entries for language semantics, semantic-version checking | The package registry, signing and trust (ECO); repository storage and merge (Kiln) |
| WIT binding generation for Ingot, and the Rust feature fallback | WIT worlds and capabilities (ECO) |
| Feature metadata for dialogs, documentation generation | Dialog rendering and handles (UIX) |
| Language service, debugger, REPL and notebooks, test and benchmark framework | The code panel and viewport (UIX); agent tools (AGT) |

### Crates

| Crate | Location | Contents | Depends on |
| --- | --- | --- | --- |
| `ingot-syntax` | `core/` | Lexer, error-resilient parser, lossless green-red tree, typed AST layer, canonical formatter, edition migrations, block grammar for the live document | none |
| `ingot-types` | `core/` | Name resolution, type inference, dimension and tolerance algebra, trait resolution, exhaustiveness, diagnostics catalog | `ingot-syntax` |
| `ingot-ir` | `core/` | Ingot IR (IIR), lowering, optimization passes, staging into regions, the reference interpreter, forward-mode differentiation | `ingot-types` |
| `ingot-codegen` | `core/` | IIR to WebAssembly, fuel and source maps, Perceus reference counting, precompilation of std | `ingot-ir`, `wasm-host` |
| `ingot-service` | `core/` | Language service (LSP 3.17 semantics), structural edits, debugger adapter (DAP), REPL and notebook kernel, test and benchmark runner | all of the above, `kiln` |
| `ingot-bindgen` | `core/` | WIT to Ingot binding generator; `ingot-macros`, the proc-macro crate for Rust-authored features | `ingot-types` |

`ingot-codegen`, `ingot-service` and `ingot-bindgen` extend the contract's crate list (CCR-ING-5). All six crates are `forbid(unsafe_code)`; machine-code loading stays in `wasm-host`.

### Design rules

1. **Pure.** No Ingot expression observes time, randomness, files, network, thread order or memory addresses. Randomness exists only as explicit, keyed counter-based streams.
2. **Strict and total by fuel.** Evaluation is call-by-value, left to right in a fixed order. Every evaluation is bounded by deterministic fuel, so it ends with a value or a typed error.
3. **Physics in types.** Dimensions, affine quantities, tolerances and approximation error are types. A unit error never reaches evaluation.
4. **Geometry by provenance.** Code never holds a raw entity index. It holds a `Query`, re-resolved on every rebuild, which fails loudly instead of rebinding.
5. **One program, three editors.** Every GUI action and agent edit is a minimal edit of the lossless tree. Nothing exists only in the GUI.
6. **No privileged code.** std is ordinary Ingot. Operations and Wasm components are called through the same `extern` declarations any package can write.
7. **Errors are values with fixes.** Every failure has a code, a reason, a source location and typed fixes that a person or an agent can apply.
8. **No macros.** Ingot has no macro system and no user code at compile time beyond constant folding. Builder blocks, attributes and generics cover what macros would; code generation happens only in `ingot-bindgen` and the Rust macro, outside the language.

**Decision D-ING-1:** Ingot is a pure, strict, expression-oriented language with immutable values, full type inference inside bodies, and required type signatures on every named function, feature and record. *Why:* signatures make each module type-check on its own, which bounds incremental recompilation to the edited module and its dependents; they also generate dialogs and documentation; local inference keeps feature bodies as short as the contract's examples. *Rejected:* whole-program Hindley-Milner inference without signatures (a change in one body can change types far away, and errors appear far from causes); dynamic typing as in CadQuery and OpenSCAD (unit errors surface at run time or never); mutable variables (they break the dataflow lowering and make literal edits non-local); lazy evaluation (costs and failures would depend on demand order, while Kiln already evaluates on demand at the level of nodes, where laziness pays).

### The language at a glance

The contract's example, in canonical Ingot:

```
use std::mech::{sketch, rect, extrude, rib, fillet, part}
use std::materials::alu_6061_t6
use std::flux::quick::peak_stress

/// L-bracket with a stiffening web.
#[feature(category: "Structure", icon: "bracket")]
pub feature bracket(
    #[ui(step: 5mm)]
    width: Length in 20mm..=400mm = 60mm,
    thickness: Length = 4mm ± 0.1mm,
    load: Force = 1.2kN,
) -> Part {
    let base = sketch(plane.xy) { rect(width, 40mm) } |> extrude(thickness)
    let web = base.face(role: end_cap).edge(longest, last(along: +y)) |> rib(height: 20mm, t: thickness)
    let body = base + web
    let solid = body |> fillet(body.edges(new), 2mm)
    let p = part(solid, name: "Bracket").material(alu_6061_t6)
    let stress = peak_stress(p, load, fixed: base.face(role: start_cap))   // a std::flux convenience
    p.require(stress < 0.6 * p.material.yield_strength(at: 20degC))
}
// width + load  →  error ING3001: cannot add Length and Force
```

Four refinements of the contract's sketch appear here. A feature parameter of type `Length` accepts a toleranced value: the body computes with the nominal, and the call records the zone for variation analysis, dialogs and PMI (D-ING-4). The top face is selected by the role that `extrude` declares, not by direction, and the two longest edges of a 60 mm by 40 mm face tie, so a second selector breaks the tie. The fillet edges are `new`: entities created by the operation that produced `body` and present in none of its inputs, the selector build123d calls `Select.NEW`. The stress comparison yields a three-valued `Truth`, because `peak_stress` returns an approximation with an error bound (D-ING-7).

## Lexical syntax

### Source text

| Aspect | Rule |
| --- | --- |
| Encoding | UTF-8 without byte-order mark. The platform layer normalizes source to NFC on load; the parser rejects non-NFC input that bypassed it (`ING0002`). |
| Line endings | LF. CRLF is accepted on input and normalized by the formatter. |
| Identifiers | Letters, digits and `_`, not starting with a digit. Unicode letters follow UAX #31 default identifiers [unverified: UAX #31 not opened]; a lint flags mixed-script identifiers. |
| Case | Functions, features, variables, fields and modules use `snake_case`; types, traits and enum variants use `PascalCase`. A deny-by-default lint enforces both (`ING9001`). |
| Statements | A newline ends a statement unless the statement is inside brackets, the line ends with a binary operator, `,` or `\|>`, or the next line begins with `.`, `\|>`, `else`, `and`, `or` or `±`. No semicolons. |
| Comments | `//` to end of line; `/* … */` nests; `///` documents the next item and `//!` the enclosing module, both in CommonMark. |
| Attributes | `#[name(args)]` on the next item, parameter or field; `#![name(args)]` on the enclosing module. |

Keywords: `and`, `as`, `else`, `enum`, `extern`, `false`, `feature`, `fn`, `for`, `if`, `impl`, `in`, `let`, `match`, `not`, `or`, `pub`, `record`, `require`, `self`, `Self`, `trait`, `true`, `try`, `type`, `use`, `where`. Contextual keywords: `kind` at item position, `table` before `{`, `package` inside `pub(…)` and as the first segment of a `use` path, `super` as a `use` path segment. `require` also appears in postfix position, `value.require(…)`, which attaches a check to that value. There is no `while` and no `return`; `for` over finite collections and the `?` operator cover their uses. `%` is the percent suffix, so remainders are the functions `rem` and `mod`.

### Numbers and quantities

| Literal | Examples | Type |
| --- | --- | --- |
| Integer | `42`, `1_000_000`, `0x1F`, `0b1010` | `Int` (64-bit, checked) |
| Real | `3.0`, `2.5e-3`, `6.02e23` | `Real` (finite IEEE 754 binary64) |
| Quantity, simple unit | `4mm`, `1.2kN`, `90deg`, `0.5rev`, `3000rpm`, `3.3V`, `100mm2` | `Quantity<D>` |
| Temperature | `20degC`, `68degF` (points); `15K`, `5delta_degC` (differences) | `Temperature` or `TemperatureDifference` (see "Affine quantities") |
| Quantity, compound unit | `9.81[m/s^2]`, `200[W/(m*K)]`, `7850[kg/m^3]`, `12[N*m]` | `Quantity<D>` |
| Ratio | `5%`, `150ppm` | `Real` (0.05, 0.000150) |
| Tolerance | `4mm ± 0.1mm`, `10mm ±(-0.1mm, +0.2mm)`, `5deg ± 30arcmin`, `1uH ± 20%` | `Tol<T>`; a percentage deviation is relative to the nominal |
| String | `"M6x1"`, `r"C:\raw"`, `"Rib {i}"`, `"{width:mm} plate"` | `String`; interpolation needs an explicit unit for quantities, so a string never depends on a display profile |

A unit attaches to its number with no space, so `2in` is two inches and `2 in r` tests membership in `r`. Lexing takes the longest unit name, and a run of letters that is not a unit is an error (`ING0201`), never a multiplication by a variable. A compound unit sits in brackets, so `9.81[m/s^2]` can never be confused with dividing by a variable named `s`. An exponent needs digits after `e` or `E`, so `1eV` is one electronvolt and `1e3eV` is a kiloelectronvolt.

The unit table is closed per edition. It holds the SI base and derived units with the SI prefixes, the radian as the angle unit, the accepted non-SI units (`min`, `h`, `d`, `L`, `t`, `bar`, `eV`, `deg`, `rev`, `arcmin`, `arcsec`, `degC`, `degF`, `degR`) and common US customary units (`in`, `ft`, `yd`, `mi`, `thou`, `lb`, `lbf`, `oz`, `psi`, `ksi`, `slug`). Prefixes compose only where defined, so `ft` is the foot and never a femtotonne, and `min` is the minute. Area and volume shorthands such as `mm2` and `cm3` are named units. Logarithmic units such as the decibel are functions, never suffixes, because their arithmetic is not multiplicative. The rotational-speed shorthand `rpm` means `rev/min`, an angular velocity. Packages cannot add units: a domain unit such as the knot becomes a constant (`std::units::knot`), so a suffix always means the same thing in every file.

The canonical spelling of every unit is ASCII (`um`, `deg`, `degC`, `ohm`). The formatter accepts `µm`, `μm`, `°`, `°C` and `Ω` on input and rewrites them, which removes the micro sign and Greek mu confusion. The tolerance operator is the one canonical non-ASCII token: `±`, with `+-` accepted on input.

**Decision D-ING-2:** Every dimensional literal carries its unit, and no file or package declares a default unit; the compiler converts a literal to its SI value by exact rational arithmetic with one correct rounding. *Why:* a default unit makes a bare number mean different things in different files, and KCL's documentation says such a number is "possibly any of them": a length, an angle or a count; exact conversion makes `25.4mm == 1in` hold bit for bit on every platform. *Rejected:* KCL's `defaultLengthUnit` setting (silent meaning depends on file context); floating-point multiplication by a conversion factor (double rounding makes equal lengths compare unequal); a unitless zero accepted as any quantity (one special case for little gain; `0mm` is explicit).

### Grammar sketch

The grammar is LL(1) after the lexer, except that `{` after an expression needs two tokens of lookahead to separate a record literal (`{ name:`), a block and a builder block. Builder blocks follow only a call's closing parenthesis. The heads of `if`, `match` and `for` cannot contain a call with a trailing block or a record literal unless parenthesized, so `if f(x) { … }` stays unambiguous. The EBNF below covers the core constructs; attributes, visibility and doc comments may precede any item, parameter or field.

```ebnf
file         = { inner_attr } { item } ;
item         = { attr } [ visibility ] ( use_decl | fn_decl | feature_decl | extern_decl
               | record_decl | enum_decl | trait_decl | impl_decl | type_alias | kind_decl | let_decl )
             | require_stmt ;                        (* a module-level check *)
attr         = "#[" path [ "(" [ arg { "," arg } ] ")" ] "]" ;
kind_decl    = "kind" ident ( "=" | ":" ) dim_expr ;   (* "=" names a dimension; ":" declares a quantity kind *)
visibility   = "pub" [ "(" "package" ")" ] ;
use_decl     = "use" use_tree ;
fn_decl      = "fn" ident [ generics ] "(" [ params ] ")" "->" type [ where_clause ] block ;
feature_decl = "feature" ident [ generics ] "(" [ params ] ")" "->" type [ where_clause ] block ;
extern_decl  = "extern" ( "fn" | "feature" ) ident [ generics ] "(" [ params ] ")" "->" type ;
params       = param { "," param } [ "," ] ;
param        = { attr } ident ":" type [ "in" expr ] [ "=" expr ] ;   (* "in": checked value range *)
record_decl  = "record" ident [ generics ] "{" [ field_list ] "}" ;
field_list   = field { "," field } [ "," ] ;
field        = { attr } ident ":" type [ "=" expr ] ;
field_types  = [ ".." type "," ] ident ":" type { "," ( ident ":" type | ".." type ) } [ "," ] ;
generics     = "<" generic_param { "," generic_param } ">" ;
generic_param = ident [ ":" bounds ] [ "=" type ] ;
bounds       = path [ "<" type_arg { "," type_arg } ">" ] { "+" path [ "<" type_arg { "," type_arg } ">" ] } ;
where_clause = "where" ident ":" bounds { "," ident ":" bounds } ;
fn_sig       = "fn" ident [ generics ] "(" [ params ] ")" "->" type [ where_clause ] ;
assoc_type   = "type" ident [ ":" bounds ] ;
use_tree     = path [ "::" ( "{" use_tree { "," use_tree } [ "," ] "}" | "*" ) ] [ "as" ident ] ;
path         = ident { "::" ident } ;
inner_attr   = "#![" path [ "(" [ arg { "," arg } ] ")" ] "]" ;
enum_decl    = "enum" ident [ generics ] "{" variant { "," variant } [ "," ] "}" ;
variant      = ident [ "(" type { "," type } ")" | "{" field_list "}" ] ;
trait_decl   = "trait" ident [ generics ] [ ":" bounds ] "{" { fn_sig | assoc_type } "}" ;
impl_decl    = "impl" [ generics ] [ path "for" ] type [ where_clause ] "{" { fn_decl | type_alias } "}" ;
type_alias   = "type" ident [ generics ] "=" type ;
let_decl     = "let" pattern [ ":" type ] "=" expr ;

type         = path [ "<" type_arg { "," type_arg } ">" ] | "[" type "]" | "(" [ type { "," type } ] ")"
               | "{" field_types "}" | "fn" "(" [ type { "," type } ] ")" "->" type
               | "impl" bounds ;                     (* parameter position only: an anonymous generic *)
type_arg     = type | dim_expr ;
dim_expr     = dim_term { ( "*" | "/" ) dim_term } ;
dim_term     = ( ident | "1" | "(" dim_expr ")" ) [ "^" rational ] ;
rational     = [ "-" ] int_lit | "(" [ "-" ] int_lit "/" int_lit ")" ;

block        = "{" { stmt } [ expr ] "}" ;
stmt         = let_decl | require_stmt | expr ;
require_stmt = "require" expr { "," ident ":" expr } ;
expr         = pipe ;
pipe         = range_expr { "|>" postfix } ;              (* right side must be a call *)
range_expr   = or_expr [ ( ".." | "..=" ) [ or_expr ] ] | ( ".." | "..=" ) or_expr ;   (* open ends allowed *)
or_expr      = and_expr { "or" and_expr } ;
and_expr     = not_expr { "and" not_expr } ;
not_expr     = [ "not" ] cmp_expr ;
cmp_expr     = tol_expr { cmp_op tol_expr } ;              (* chains: a < b <= c *)
cmp_op       = "==" | "!=" | "<" | "<=" | ">" | ">=" | "in" ;
tol_expr     = add_expr [ "±" ( add_expr | "(" add_expr "," add_expr ")" ) ] ;   (* (lower, upper) deviations *)
add_expr     = mul_expr { ( "+" | "-" ) mul_expr } ;
mul_expr     = unary { ( "*" | "/" | "&" ) unary } ;
unary        = [ "-" | "+" ] power ;
power        = postfix [ "^" unary ] ;                      (* right-associative; -x^2 = -(x^2) *)
postfix      = primary { "." ident [ call_args [ block ] ] | "." "require" call_args
               | call_args [ block ] | "[" expr "]" | "?" } ;
call_args    = "(" [ arg { "," arg } [ "," ] ] ")" ;
arg          = [ ident ":" ] expr | ".." expr ;             (* ..record spreads named arguments *)
primary      = literal | path | "(" expr { "," expr } ")" | "[" [ expr { "," expr } ] "]"
               | record_lit | map_lit | table_lit | if_expr | match_expr | for_expr
               | lambda | "try" expr | block ;
lambda       = "|" [ ident [ ":" type ] { "," ident [ ":" type ] } ] "|" expr ;
record_lit   = path "{" [ fields ] "}" | "{" fields "}" ;     (* without a path, at least one field *)
fields       = ( ".." expr | ident ":" expr ) { "," ( ".." expr | ident ":" expr ) } [ "," ] ;
map_lit      = "[" expr "=>" expr { "," expr "=>" expr } [ "," ] "]" ;
literal      = int_lit | real_lit | quantity_lit | percent_lit | string_lit | "true" | "false" ;
quantity_lit = ( int_lit | real_lit ) ( unit | "[" unit_expr "]" ) ;   (* no space before the unit *)
unit_expr    = unit_term { ( "*" | "/" ) unit_term } ;
unit_term    = ( unit | "(" unit_expr ")" ) [ "^" rational ] ;
table_lit    = "table" "{" ident { "|" ident } { row } "}" ;
row          = expr { "|" expr } ;              (* one row per line; a lambda in a cell needs parentheses *)
pattern      = "_" | ident | literal | range_pat | path [ "(" pattern { "," pattern } ")" ]
               | path "{" ident [ ":" pattern ] { "," ident [ ":" pattern ] } [ "," ".." ] "}"
               | "(" pattern { "," pattern } ")" | pattern "|" pattern ;
range_pat    = literal ( ".." | "..=" ) [ literal ] | ( ".." | "..=" ) literal ;
if_expr      = "if" expr block [ "else" ( if_expr | block ) ] ;
match_expr   = "match" expr "{" { pattern [ "if" expr ] "=>" expr "," } "}" ;
for_expr     = "for" pattern "in" expr block ;
```

Named arguments may appear in any position; positional arguments fill the remaining parameters in declaration order, so `rect(center: origin, length, width)` is valid. Any parameter may be passed by name. A lint (`ING9201`) asks for names on positional arguments after the second, because named arguments survive signature changes and merge as sets. An argument that begins with `..` spreads a record; an open-start range in that position needs parentheses, `(..5mm)`. Within one block, each `let` name is unique (`ING1102`), so every statement has one stable name in the feature tree; inner blocks may shadow outer names. There is no ad hoc overloading: one name has one signature, and traits provide polymorphism.

Tokens follow the lexical rules above: `ident`, `int_lit`, `real_lit`, `string_lit`, `percent_lit` (a number followed by `%` or `ppm`) and `unit`, one of the closed unit table's names.

Operator precedence, from loosest to tightest: `|>`; ranges; `or`; `and`; `not`; comparisons (chainable); `±`; `+` and `-`; `*`, `/` and `&`; unary minus; `^`; postfix. On Bodies and on sets, `+` is union, `-` is difference and `&` is intersection, so intersection binds tighter, as in set algebra. Boolean logic uses the words `and`, `or` and `not`, so `&` never means two things.

A call followed by a block, as in `sketch(plane.xy) { … }`, passes the block as a builder argument (see "Builder blocks"). `x |> f(a)` means `f(x, a)`: the left side becomes the first parameter. Methods (`x.f(a)`) come only from `impl` blocks and traits, so `.` is type-directed and `|>` chains free functions and features.

## Type system

### Primitive and core types

| Type | Values | Notes |
| --- | --- | --- |
| `Bool` | `true`, `false` | `if` conditions and `match` guards take `Bool`, or `Truth` under D-ING-7 |
| `Int` | 64-bit signed integers | Overflow is a typed failure (`ING6101`), never wraparound |
| `Real` | Finite IEEE 754 binary64 values | Exactly `Quantity<1>`. NaN and infinities are not values: an operation that would produce one fails with `NumericError` (`ING6102`) at that expression |
| `Quantity<D>` | A `Real` magnitude in coherent SI units with dimension `D` | Checked at compile time, erased at run time |
| `Temperature` | An absolute temperature: a point on the thermodynamic scale | Affine; see below |
| `Complex<Q>` | Pairs of quantities of one dimension | The imaginary unit is the constant `im` |
| `Decimal` | Exact decimal numbers: a 128-bit integer count of 10⁻⁹ | For money and counted data; checked overflow; literals adopt it by expected type, exactly |
| `String` | Immutable UTF-8 text in NFC | For names, labels and messages; never parsed by the engine |
| `ExternalText` | Text from outside the design (imported names, component messages), written `external("…")`, with its origin | Never implicitly a `String`, so untrusted text stays labelled (AGT) |
| `()` | The unit value | |
| `Truth` | `True`, `False`, `Undecided(reason)` | Three-valued result of comparing approximate or toleranced values |
| `Approx<T>` | A value with an `ErrorBound` | The language form of the contract's `ErrorBound` |
| `Tol<T>` | A toleranced specification | See "Tolerances" |
| `Body`, `Part`, `Assembly`, `Instance`, `Field<Domain, V, A…>`, `Material` | Core cross-subsystem types | Opaque handles to values that Kiln holds; see "Geometry in the language" |
| `Query<K>`, `Entity<K>` | Selections and resolved entities | `K` is `Face`, `Edge`, `Vertex`, `Region`, `Point` or `ShapeAspect` |
| `Point3`, `Vec3<D>`, `Direction`, `Transform`, `Plane`, `Axis`, `CoordSys` | Geometric values | `Point3` is affine over `Length`; `Direction` is a unit vector |
| `Seed`, `Rng` | A 64-bit seed; a Philox key | See "Explicit randomness" |
| `Expr<T, Out>` | A staged symbolic value; `Expr<T>` abbreviates `Expr<T, {}>` | See "Sketches and constraints" |

`Real` is `Quantity<1>`, so `width / 2mm` is a `Real` and every dimensionless ratio is one type. `Int` multiplies quantities directly, so `i * 6mm` needs no conversion; an `Int` above 2⁵³ in magnitude fails that conversion with `ING6103` rather than rounding silently.

### Dimensions

A dimension is a vector of rational exponents over eight base dimensions: the seven SI base dimensions (length `L`, mass `M`, time `T`, electric current `I`, thermodynamic temperature `Θ`, amount of substance `N`, luminous intensity `J`) plus plane angle `A`. Solid angle is `A²`, so the steradian is the square radian. Exponents are rational because engineering needs them: fracture toughness is `MPa*m^(1/2)` and noise density is `V/Hz^(1/2)`.

```
kind Length = L                          // std prelude: named dimensions
kind Angle = A
kind Stress = M / (L * T^2)
kind Torque: M * L^2 / T^2               // a kind: same dimension as Energy, not interchangeable
kind Energy: M * L^2 / T^2
type Velocity = Quantity<L / T>          // aliases are ordinary type aliases
```

Ingot adds no other base dimension. Counts are `Int`; a revolution or a cycle is an angle (`1rev` is 2π rad); and information quantities have no use in physical design that `Int` does not cover. Currency is std's `Money<C>`, as MFG requests (CCR-MFG-4): a `Decimal` amount with an ISO 4217 currency as a type parameter, outside the dimension algebra, so adding two currencies without a dated rate fails to compile.

`kind X = D` names a dimension. `kind X: D` declares a quantity kind in the sense of ISO 80000: a nominal refinement of `D` that does not add to, subtract from or compare with another kind of the same dimension. Arithmetic results are unkinded until they meet an annotation, so `force * lever` flows into either a `Torque` or an `Energy` slot. Adding a `Torque` to an `Energy` fails with `ING3002`, which offers an explicit `as Energy` cast. std declares kinds only where confusion causes real errors: torque and energy, frequency and radioactive activity, absorbed dose and dose equivalent. The mp-units library documents the same distinction: quantities of one dimension "are not necessarily of the same kind", and hertz, becquerel and baud share `T⁻¹`.

Arithmetic rules:

| Expression | Rule |
| --- | --- |
| `a + b`, `a - b`, comparisons, `min`, `max` | Same dimension and compatible kind |
| `a * b`, `a / b` | Dimensions add or subtract exponent-wise; `Int / Int` is a `Real`, and `div`, `rem` and `mod` are the integer operations |
| `a ^ n` | `n` must be a compile-time rational constant unless `a` is dimensionless |
| `sqrt(a)`, `cbrt(a)` | Exponents halve or divide by three; always defined over rationals |
| `sin`, `cos`, `tan` | Take `Angle`, return `Real` |
| `asin`, `acos`, `atan`, `atan2(y, x)` | Return `Angle`; `atan2` needs `y` and `x` of one dimension |
| `exp`, `ln`, `log10` | Take and return `Real`; `ln(p / p0)` is the idiom for a dimensional argument |

**Decision D-ING-3:** Plane angle is a base dimension, the radian is its coherent unit, and Ingot never cancels it implicitly. Formulas that rely on the SI convention rad = 1 state it with the constant `radian`, as in `omega * r / radian`, or call a named std function (`arc_length`, `tangential_speed`, `angular_frequency`). Torque keeps its conventional dimension and unit, newton metre, as a kind distinct from energy; `shaft_power(torque, speed)` and `rotational_work(torque, angle)` absorb the radian once, in std. *Why:* the contract names angle as a dimension; tracking it catches degree-radian mix-ups and the 2π error between angular velocity and frequency, whose values mp-units notes differ by a factor of 2π; keeping newton metres for torque matches every datasheet and catalog part. *Rejected:* angle dimensionless as in the SI (`3000rpm` would silently become a frequency of 314 Hz); torque in newton metres per radian as in mp-units' experimental strong angular system (correct, but every torque literal from a datasheet would need rewriting); implicit cancellation of `A` at annotations (reintroduces the 2π error it exists to catch).

### Inference

Every named item states its signature; bodies are inferred. The checker is bidirectional: types flow down from signatures and annotations, and up from literals and calls. Unification extends ordinary type unification with dimension equations. Because exponents are rational, the equations are linear over ℚ, so Gaussian elimination solves them and yields a most general solution. F# checks units of measure with integer exponents ("integral powers are supported") and offers unit-generic functions over `float<'u>`; Ingot extends the same idea to rational exponents and infers dimension arguments at call sites. Dimension parameters are erased at run time, so a function generic only over dimensions compiles once.

```
fn rms<D>(xs: [Quantity<D>]) -> Quantity<D> {
    sqrt(sum(xs.map(|x| x * x)) / xs.len())     // D² → D, solved by the checker
}
fn spring_rate(f: Force, x: Length) -> Quantity<M / T^2> { f / x }   // N/m checked
```

The core typing rules for arithmetic, written as premises ⇒ conclusion:

| Rule | Premises | Conclusion |
| --- | --- | --- |
| Add, Sub | `a : Quantity<D>`, `b : Quantity<D>`, kinds compatible | `a ± b : Quantity<D>`, with the shared kind if both have it |
| Mul, Div | `a : Quantity<D1>`, `b : Quantity<D2>` | `a * b : Quantity<D1·D2>`, `a / b : Quantity<D1/D2>`, unkinded |
| Pow | `a : Quantity<D>`, `n` a constant in ℚ | `a ^ n : Quantity<Dⁿ>` |
| Affine | `p, q : P` with `P: Affine`, `d : P::Delta` | `p - q : P::Delta`; `p ± d : P` |
| Tol lift | Any operand of type `Tol<T>`, the others exact | Result `Tol<U>`, where `U` is the exact rule's result |
| Approx lift | Any operand of type `Approx<T>`, the others exact | Result `Approx<U>` |
| Compare | Exact operands | `Bool` |
| Compare, toleranced | Any operand `Tol<T>` | Error `ING4101`, with fixes that state the meaning (see "Arithmetic on tolerances") |
| Compare, approximate | Any operand `Approx<T>` | `Truth` |
| Mixed | One operand `Tol<T>`, another `Approx<U>` | Error `ING4102`: convert the tolerance with `.limits()` first |

Inference does not generalize `let` bindings inside bodies, and lambdas are monomorphic. Integer literals adopt the expected numeric type (`Int`, `Real` or `Decimal`) and default to `Int`; real literals adopt `Real` or `Decimal` and default to `Real`. A literal becomes a `Decimal` exactly or fails to compile (`ING2003`) when it has more than nine fractional digits. There is no implicit conversion between `Int` and `Real` except multiplication and division of quantities by `Int`, and `.to_real()`.

Five coercions exist, each at a fixed place, and the language service shows each one as an inlay hint:

1. `T` to `Option<T>` at argument and record-field positions, so `mirror: plane.yz` fills an `Option<Plane>` parameter.
2. A `Tol<T>` into a parameter, record field or enum payload declared as `T` (D-ING-4).
3. An unkinded quantity to a kind of the same dimension, at annotations and parameters.
4. A value of type `P` to an enum whose declaration marks one variant with payload `P` as `#[implicit]`, at argument positions. MEC's `Extent` marks `Blind`, so `extrude(10mm)` means `extrude(Blind(10mm))`.
5. An `Approx<T>` to `T` at feature and operation argument positions only, under the rule in "Approximate values as inputs".

### Affine quantities

Absolute temperature is a point, not a quantity. `Temperature` points and `TemperatureDifference` (`Quantity<Θ>`) obey the affine-space rules that mp-units documents: point minus point is a difference, point plus or minus a difference is a point, and points never add, multiply or divide. Pint enforces the same rules and raises `OffsetUnitCalculusError` for ambiguous operations on offset units such as degrees Celsius.

| Literal or expression | Type | Value stored |
| --- | --- | --- |
| `20degC`, `68degF` | `Temperature` | 293.15 K from absolute zero |
| `15K`, `27degR`, `5delta_degC`, `9delta_degF` | `TemperatureDifference` | 15 K, 15 K, 5 K, 5 K |
| `absolute_zero + 77K` | `Temperature` | 77 K |
| `t1 - t2` | `TemperatureDifference` | |
| `t.absolute()` | `TemperatureDifference` | Kelvin above absolute zero, for `pow`, ideal gas and radiation laws |
| `200[W/(m*K)]` | `Quantity<M*L/(T^3*Θ)>` | Temperature units inside a compound unit always mean differences |
| `t1 + t2`, `2 * t`, `20[J/degC]` | Error `ING3201` | Fix-its: `.absolute()`, a difference, or `K` in the compound unit |

`K` and `degR` denote differences because they are the coherent units of the dimension; `degC` and `degF` denote points because their scales are defined by an origin. `lerp(t1, t2, s)` and `mean([t…])` are defined for points, as affine combinations whose weights sum to one. `Point3` and `Vec3<Length>` follow the same rules: `p - q` is a vector and `p + q` is an error. Gauge pressure has no unit in the table, because its reference atmosphere is not a constant; designs write `p_atm + 2bar`.

### Display and storage

| Concern | Rule |
| --- | --- |
| Storage | Every quantity is stored in coherent SI units as binary64: metres, kilograms, seconds, radians, kelvin. Anvil and Flux receive SI values (Anvil: "Lengths are meters and angles are radians inside Anvil"). |
| Literals | Source keeps the literal as written. The stored value is the correctly rounded binary64 nearest the exact rational value, so `25.4mm == 1in` holds on every platform. |
| Display | A display profile maps dimensions to units (`Length → mm`, `Stress → MPa`, `Temperature → degC`) per package, per user or per view. Display never changes a value. |
| Printing | A value prints as the shortest decimal in the display unit that converts back to the same binary64 value, so `0.1mm` prints as `0.1mm` [unverified: shortest round-trip printing as in the Ryū algorithm; paper not opened]. |
| Generated literals | When the visual editor or an agent writes a value, the literal keeps the unit already present at that position, otherwise the display unit. |

### Records, enums and tagged unions

```
/// A dowel pin specification.
pub record DowelSpec {
    diameter: Length,
    length: Length,
    chamfer: Option<Length> = none,      // fields may have defaults
}

pub enum Extent<Q = Length> {             // abridged from MEC; generic with a default argument
    #[implicit] Blind(Q),                 // extrude(10mm) means extrude(Blind(10mm))
    Symmetric(Q),
    UpTo(Query<Face>),
    ThroughAll,
}

let spec = DowelSpec { diameter: 6mm, length: 20mm }
let longer = DowelSpec { ..spec, length: 30mm }     // functional update
let kind = match extent {
    Blind(d) if d > 50mm => "deep",
    Blind(_) | Symmetric(_) => "blind",
    UpTo(_) | ThroughAll => "through",
}
```

A record with exactly one field may be constructed by calling its name, as in `Seed(7)` or `ItemNumber("GP1-100")`. Records are nominal when declared and structural when written as `{ a: Length, b: Int }`. A record literal without a path adopts the expected record type, as in `let heavy: Params<bracket> = { width: 80mm }`, and is structural when there is none. A structural record type may spread another record type, `{ item: ItemNumber, ..Params<bracket> }`, when the field sets are disjoint, or when shared fields have identical types, which merge. Flux uses this for `solve`. A symbolic expression type carries the record of derived outputs that its functions declare, `Expr<T, Out>`, and combining expressions spreads their `Out` records. `solve` returns `{ ..Trials, ..Out }`, so `result.von_mises` is a typed field (FLX). Enums are tagged unions with exhaustive `match`. Where the expected type is a known enum, a bare variant name resolves in that enum, so `mode: Geometry` fills a `PatternMode` parameter; elsewhere the variant is qualified (`PatternMode::Geometry`). An enum marked `#[non_exhaustive]` may gain variants in a minor release, and matches over it outside its package need a wildcard arm.

### Generics and traits

Type parameters are monomorphized; dimension parameters are erased. A function that must know a dimension at run time, such as an accessor that checks the units recorded in a Field produced by a Wasm component, declares the bound `D: Dim`, which passes the dimension's exponent vector as a hidden argument. A kind name used as a type, such as `Length`, means `Quantity` of that dimension or kind. In `Field<Domain, V, A…>`, type arguments after the value type form the axis tuple, so `Field<Part, Temperature, Time>` is sugar for `Field<Part, Temperature, (Time,)>` (FLX). Traits declare methods, associated types and associated constants, with default methods. Coherence follows Rust's orphan rule: an `impl` lives in the package of the trait or of the type, so two packages can never supply conflicting implementations. `dyn Trait` boxes a value with its method table for heterogeneous lists.

| std trait | Purpose | Implemented by |
| --- | --- | --- |
| `Eq`, `Ord`, `Hash` | Equality, the canonical total order, canonical hashing | Numbers, strings, records and enums by derivation, `EntityId`, and `Query` by its canonical plan, so Flux's `[faces => value]` boundary maps work |
| `Add`, `Sub`, `Mul`, `Div`, `Neg` | Operators | Quantities, vectors, Bodies (`+`, `-`), queries |
| `Affine` | Point types with an associated `Delta` | `Temperature`, `Point3` |
| `Transformable` | `.moved(by: Transform)` | Bodies, Parts, points, planes, coordinate systems, queries |
| `Patternable`, `Mirrorable` | Inputs to `pattern` and `mirror` (MEC) | Bodies, tool bodies, features, face sets |
| `Selectable` | Entity kinds a `Query<K>` may select | `Face`, `Edge`, `Vertex`, `Region`, `Point`, `ShapeAspect` |
| `Measure` | `.measure()` returning `Approx<Q>` | Distances, angles, areas, volumes, mass properties |
| `Feature` | Implemented by every `feature`: associated types `Params` and `Output`, plus `metadata()` | Lets `family`, `pattern(mode: Feature)` and agent tool schemas work over any feature generically |
| Material model traits, such as `LinearElastic` | Property and constitutive interfaces that std physics consumes (COV, FLX) | Material records and model packages |
| `Check` | A predicate that a check can evaluate and report | `Bool`, `Truth`, std check records |
| `Error` | A typed failure with a code, message and fixes | `ResolveError`, Anvil `OpError`, MEC `FeatureError`, user errors |

### Option, Result and failures

`Option<T>` has `some(x)` and `none`; `Result<T, E>` has `ok(x)` and `err(e)`. Constructors of std's core enums are lower case by long-standing convention, the one exception to the naming rule. The postfix `?` turns `err(e)` into a failure of the enclosing feature and `none` into `ING6201` with the expression's span. A failure value is never a design: `fail(e)` raises one explicitly, and `e.fixes()` lists its fixes. Failures themselves are described under "Errors, failures and checks".

### Collections and ranges

| Type | Literal | Semantics |
| --- | --- | --- |
| `[T]` | `[1mm, 2mm, 3mm]` | Persistent list; updates reuse storage in place when uniquely referenced (Perceus) |
| `Map<K, V>` | `["M6" => 6.6mm, "M8" => 9mm]` | Ordered by `K`'s canonical order, so iteration is deterministic; `Map::empty()` is the empty map |
| `Set<T>` | `set([…])` | Ordered |
| Tuples | `(a, b)` | Structural |
| `Range<T>` | `0..8`, `20mm..=400mm`, `100mm2..`, `..=5mm` | Half-open or closed, optionally open-ended; also the interval type (`r.lo`, `r.hi`, `x in r`). `x in r` is three-valued when `x` is an `Approx` |
| `Table<R>` | `table { … }`, `table("rows.csv")` | Rows of a record type, checked against units in headers |

Fixed-size vectors and matrices of quantities, such as `Vec3<Length>` and `Mat3<Stress>`, are std types over the same dimension algebra. A matrix whose rows and columns carry different dimensions, as a Jacobian does, has the type `Mat<R, C>` with a dimension per row and per column, and multiplication checks that the inner dimensions cancel. There is no hash map with per-process seeds: iteration order is part of the value. A `Range` of quantities iterates only with an explicit step, as in `(0mm..=10mm).step(2mm)`, because a default step of one metre would be a silent assumption. The std reductions `sum`, `product`, `min` and `max` have a defined evaluation order (a fixed pairwise tree over indices), and `fsum` returns the correctly rounded sum.

## Tolerances, approximations and truth

Three different things can make a number uncertain, and Ingot gives each its own type. A tolerance is a design specification: the part may vary within it, on purpose. An approximation is a computed value with numerical error, such as a stress from a coarse solve. A truth value is the honest result of comparing either of them with a limit.

| Type | Meaning | Produced by | Consumed by |
| --- | --- | --- | --- |
| `Tol<T>` | Allowed variation of a manufactured characteristic | Designers, fit codes, catalog parts | Geometry (nominal), PMI, variation analysis, checks |
| `Approx<T>` | A computed value and its `ErrorBound` | Measurements, Field reductions, solves | Checks, reports, control flow with explicit decisions |
| `Truth` | `True`, `False` or `Undecided(reason)` | Comparisons of approximate values | `require`, `if` (fails on `Undecided`), `match` |

### `Tol<T>`

```
pub record Tol<T: Toleranceable> {
    nominal: T,
    lower: T::Delta,              // signed deviation from nominal
    upper: T::Delta,              // signed deviation; lower <= upper
    basis: TolBasis = WorstCase,  // or Statistical(Dist)
    form: TolForm,                // how it was written: Symmetric, Deviations, Limits, Fit(code), Basic
}
```

`Toleranceable` covers `Quantity<D>`, `Real` and `Temperature`, whose `Delta` is `TemperatureDifference`. The written form is kept so PMI and drawings show the tolerance as the designer wrote it, as limits or as plus and minus deviations.

| Form | Ingot | Limits |
| --- | --- | --- |
| Symmetric | `4mm ± 0.1mm` | 3.9 mm to 4.1 mm |
| Deviations | `10mm ±(-0.1mm, +0.2mm)` | 9.9 mm to 10.2 mm; lower first, as in a range; signs mandatory |
| Unilateral | `6mm ±(0mm, +0.05mm)` | 6 mm to 6.05 mm |
| Limits | `tol(9.9mm..=10.2mm)` | Nominal is the mid-limit, 10.05 mm |
| Fit code | `fit(10mm, H7)` | Tabulated by ISO 286-1:2010, which ISO reviewed and confirmed in 2026; tables in `std::mech::fits` (MEC) |
| Basic | `basic(30mm)` | A theoretically exact dimension: zero deviations, framed in PMI, toleranced by a GD&T control |

A tolerance whose `lower` exceeds `upper` fails to compile (`ING4001`), as does a deviation of the wrong dimension (`ING4002`). A dimensionless deviation is relative only when written as a `%` or `ppm` literal, as in `1uH ± 20%`; `4mm ± 0.1` is `ING4002`, never a silent 10%.

**Decision D-ING-4:** A `Tol<T>` may be supplied wherever a parameter, record field or enum payload is declared as `T`. The slot holds the nominal and a reference to the tolerance's site. Reading the slot in an expression yields the nominal; passing its value on unchanged, as an argument, into another field or payload, or into a `let` binding, forwards the reference. Every feature call records the tolerances it receives, so variation analysis, dialogs, PMI and `tolerances(x)` can find them. Code that needs the zone itself declares the type as `Tol<T>`. *Why:* this keeps the contract's `thickness: Length = 4mm ± 0.1mm` exactly; forwarding carries the tolerance to the call that realizes it, so `extrude(thickness)` can attach the depth tolerance as PMI to the faces it creates; and geometry stays at nominal, as CAD convention expects. *Rejected:* a tolerance on every `Length` value (temporaries and large lists would pay for tracking; here only slots carry a 32-bit site reference); requiring `.nominal` at every use (noise, and the tolerance would be lost to analysis and PMI); dropping the tolerance at the first call boundary (the PMI would never reach the geometry).

The coercion is the second of the five fixed coercions listed under "Inference". The language service marks each nominal use with an inlay hint (`≈ nominal`) and each forwarding with `→ ±`, so a reader always sees where a zone travels and where only its nominal is used.

### Arithmetic on tolerances

`Tol` arithmetic is worst case by default, and it is exact for linear stacks. A tolerance site is the expression that creates a tolerance: a `±` expression, `tol(…)` or `fit(…)`. Each site owns one noise symbol εᵢ in [−1, 1], and a computed `Tol` is an affine form: a center plus one coefficient per symbol. Forwarding passes the same symbols along, so a tolerance used in several features is still one source of variation. This is affine arithmetic, introduced by Comba and Stolfi (1993) and surveyed by de Figueiredo and Stolfi (2004): forms that share a symbol are correlated, which removes the dependency problem of interval arithmetic.

| Operation | Result |
| --- | --- |
| `a + b`, `a - b`, `k * a`, `a / k` with exact `k` | Exact affine combination; shared symbols combine, so `a - a` has zero width |
| `a * b`, `a / b`, `sqrt(a)`, `sin(a)`, other smooth functions | First-order term per symbol, plus one new symbol whose coefficient bounds the remainder over the joint box |
| `a + x`, `a * x` with an exact quantity `x` | The nominal moves or scales; symbols scale |
| `a < b`, `a == b` and other comparisons | Error `ING4101`: comparing tolerances needs a stated meaning. Fix-its offer `a.max() < b.min()` (always), `a.nominal < b.nominal` and `yield_of(…)` |

Rounding errors enter the remainder symbol, as affine arithmetic prescribes, so `.limits()` is a guaranteed enclosure in binary64. The remainder symbol is identified by the expression's site, so it is the same on every rebuild.

```
let bore  = fit(20mm, H7)                  // 20.000 to 20.021 mm [unverified: ISO 286-2 table values]
let shaft = fit(20mm, g6)                  // 19.980 to 19.993 mm [unverified: ISO 286-2 table values]
let clearance = bore - shaft               // Tol<Length>, affine in two symbols
clearance.limits()                         // 0.007mm..=0.041mm, exact for this linear stack
clearance.rss()                            // statistical limits at ±3σ (see below)
clearance.contributors()                   // [(bore, 61.8%), (shaft, 38.2%)] by worst-case share
```

Statistical combination is always an explicit call, as MEC requires. The two calls follow the GUM family of the JCGM: `.rss(k:)` is first-order propagation as in JCGM 100:2008, and `.monte_carlo(n:, rng:)` propagates distributions as JCGM 101:2008 (Supplement 1) describes, with an explicit `Rng`. `.rss(k: 3)` treats each symbol as an independent random variable with the distribution its site declares, combines the linear coefficients by root-sum-square and adds any nonlinear remainder at worst case, reporting how much of the result it contributes. A site declares its distribution with `.statistical(Normal(cp: 1.33))`, `.statistical(Uniform)` or a measured process capability from an MFG process profile. A site that declares none uses `std::tol::default_distribution`: normal and centered, with the limits at ±3σ (Cp = 1). Every statistical report prints the distributions it assumed. `.statistical(…)` also marks the PMI as statistically toleranced.

Sites may share variation. `.statistical(Normal(cp: 1.33), group: lot_a)` splits a site's deviation into a component shared by every site in the group and an individual component, with `between:` and `within:` distributions when both are known. Worst-case arithmetic keeps one symbol per group and one per site, so components from one reel or one fixture correlate, as ELX's Monte Carlo needs.

A symbol stands for one manufactured characteristic, and the rules follow from that:

1. A `Tol` value written in code has one symbol per site, so reusing the value models one characteristic. A site inside a loop or pattern gets one symbol per iteration, because its identity includes the iteration, as `OpSite` does.
2. A tolerance read from geometry, such as `aspect.size_tol()` or a dimension carried as PMI, has a symbol keyed by the aspect's `EntityId` and the Instance path. Four holes made from one specification therefore vary independently, and so do two Instances of one Part.
3. `t.independent(key)` makes an explicit independent copy of a code-level value, for stacks written without geometry, such as two spacers that share one specification.

**Decision D-ING-5:** `Tol` arithmetic uses affine forms over per-site noise symbols: worst case by default, exact for linear stacks, conservative with an explicit remainder for nonlinear ones, and statistical only through explicit calls. *Why:* engineers rely on worst-case stack-ups being exact for linear chains, and correlation between repeated uses of one dimension is the most common source of wrong stack-ups in interval-style tools; affine forms give both at linear cost. *Rejected:* interval arithmetic (overestimates any expression that uses a dimension twice); implicit RSS (hides an assumption about the process); Monte Carlo inside ordinary arithmetic (nondeterministic unless seeded, slow, and still an assumption about distributions).

3D variation analysis is MEC's: it perturbs toleranced sites and aspects per sample and re-evaluates the assembly. Ingot supplies the two primitives it needs. `tolerances(x)` lists the tolerance sites recorded by the feature calls that produced `x`. `vary(f, sites)` evaluates a closure with chosen sites replaced by sample values, using the literal-override mechanism of the Kiln contract, so every sample is an ordinary cached evaluation.

### GD&T controls as types

MEC owns the GD&T model: the `GeometricTolerance`, `Datum` and `DatumSystem` records and the validators. Ingot owns how controls attach to geometry and which mistakes the type checker catches.

1. **Aspects are typed.** A `Query<Aspect<K>>` selects shape aspects, such as holes and planar faces, whose kind `K` is known statically when the producing feature declares it. `hole(…)` produces `Aspect<OfSize>`, `extrude` caps produce `Aspect<Planar>`, and recognition of imported geometry produces `Aspect<Any>`.
2. **Controls are values.** `position(…)`, `flatness(…)` and the other characteristics are functions returning `GeometricTolerance` records; one record is one feature control frame, with its characteristic, zone, modifiers and datum references. Their signatures carry the standards' rules as trait bounds: a material condition modifier requires a target with `K: OfSize`, and a datum feature reference at maximum material boundary requires a datum aspect that is a feature of size.
3. **Attachment is a typed attribute.** `part.tolerance(target, control)` returns a new Part whose Body carries the control as an attribute keyed by the target's `EntityId`s, through Anvil's attribute side table and its propagation rules. The target is a `Query`, so it re-resolves on every rebuild and fails with a `ResolveError` instead of moving.
4. **Dialects are modules.** `std::mech::gdt::asme` implements ASME Y14.5-2018, reaffirmed in 2024 and on stabilized maintenance. `std::mech::gdt::iso` implements ISO GPS: ISO 1101:2017 (confirmed in 2022), ISO 5459:2024 for datums, ISO 14405-1:2025 for linear sizes, ISO 8015:2011 for fundamentals and ISO 22081:2021 for general specifications. A module imports one dialect explicitly, and the manifest key `gdt-dialect` names the design's dialect; a module that imports the other one fails with `ING4302`.
5. **Deleted symbols are tombstones.** MEC records that ASME Y14.5-2018 deleted concentricity and symmetry. The ASME module declares them as `#[removed(in: "ASME Y14.5-2018", instead: "position, profile or runout")]`, so a call fails to compile with that explanation and fix-its, rather than with "unknown name".

```
use std::mech::gdt::asme::{datum, position, flatness, profile, mmc, mmb, dia}

let a = datum("A", plate.face(role: start_cap))
let b = datum("B", plate.face(role: side(e_left)))
let c = datum("C", plate.aspect(created_by: locating_pin_hole))   // Aspect<OfSize>
let holes = plate.aspects(created_by: mount_holes)               // Query<Aspect<OfSize>>
plate
    .tolerance(holes, size: fit(8mm, H8))
    .tolerance(holes, position(dia(0.1mm), mmc, datums: [a, b, c.at(mmb)]))
    .tolerance(a.aspect, flatness(0.02mm))
    .tolerance(plate.faces(all), profile(0.2mm, datums: [a, b, c]))
// position(dia(0.1mm), mmc, …) on plate.face(role: start_cap)
//   → error ING4201: maximum material condition needs a feature of size; start_cap is Aspect<Planar>
```

Rules that need resolved geometry, such as whether a datum system constrains every degree of freedom it must, run at build time and fail with MEC's `InvalidControl { rule, clause }` or `DatumUnderdefined { dof }`. ASME Y14.5.1-2019 gives the mathematical definition behind these rules; its ASME page describes it as consistent with Y14.5M-1994, so where it and Y14.5-2018 differ, MEC states which governs [unverified: alignment of Y14.5.1-2019 with Y14.5-2018].

**Decision D-ING-6:** GD&T controls are ordinary records returned by dialect-specific functions, legality rules are trait bounds on typed aspects where the aspect kind is static, and the remaining rules run at build time. *Why:* the commonest GD&T errors (material modifiers on surfaces, deleted symbols, mixed dialects) become compile errors at the line that causes them, with no special syntax. *Rejected:* a separate GD&T sublanguage (a second grammar for a few dozen records); validation only at build time (errors appear late and far from their cause); string-encoded feature control frames (untyped).

### `Approx<T>` and `Truth`

```
pub record Approx<T> {
    value: T,
    bound: ErrorBound,            // the shared record { value, norm, kind }; value in T's dimension, a Length for Bodies
    flags: Set<ValueFlag> = set([]),   // Singular, OutsideValidity(model), ScaleSeparation, Preview, …
}
```

`Approx<T>` is the language form of the contract's `ErrorBound` for plain values. Measurements (`body.volume()`, `distance(a, b)`), Field reductions (`stress.max()`) and Wasm component results with declared errors return it. Fields themselves carry Flux's `ErrorBudget`; reducing a Field yields an `Approx` whose bound is the budget's total for that reduction.

Arithmetic propagates bounds by first-order rules with the product term kept: |xy − x̃ỹ| ≤ |x̃|·e_y + |ỹ|·e_x + e_x·e_y. Division fails with `ING6104` when the divisor's enclosure contains zero. The guarantee of a result is the weakest of its inputs, in Flux's order `Guaranteed` > `Estimated` > `Indicator` > `Unknown`, and flags are united. Bounds use outward rounding, so a `Guaranteed` bound stays guaranteed in binary64.

A comparison involving an `Approx` returns a `Truth`; a comparison of exact values, including `Tol` limits, is `Bool`. Equality `==` on an `Approx` is three-valued as well: it is `False` when the enclosures are disjoint and `Undecided` otherwise, because real numbers known only within bounds are never provably equal. For `x < y`:

| Outcome | Condition |
| --- | --- |
| `True` | Upper end of `x`'s enclosure < lower end of `y`'s, all bounds known and no blocking flags |
| `False` | Lower end of `x` ≥ upper end of `y`, under the same conditions |
| `Undecided(WithinBound { margin, needed })` | The enclosures overlap; `needed` is the bound that would decide |
| `Undecided(UnknownError)` | Any bound is `Indicator` or `Unknown`; Flux's particle results with unknown error never pass |
| `Undecided(Flagged(flag))` | A blocking flag is set, such as `Singular` or `OutsideValidity`, with the fix the flag carries |

`and`, `or` and `not` on `Truth` follow Kleene's strong three-valued logic, so `False and Undecided` is `False`. An `Estimated` bound can decide a comparison, but the outcome records its basis, and a check may demand `evidence: Guaranteed`.

**Decision D-ING-7:** Comparisons of approximate values return a three-valued `Truth`. `require` reports `Undecided` as its own outcome; `if` and `match` guards accept a `Truth` but fail with `ING6401 UndecidedBranch`, carrying the margin and the accuracy needed, when it is `Undecided`. *Why:* a binary comparison on an estimate silently passes designs whose margin lies within numerical error, which FLX's D-FLX-15 forbids for checks; failing loudly in control flow keeps feature logic honest without forcing a `match` at every measurement. *Rejected:* comparing the estimate only (silent error); making `if` on a `Truth` a compile error (every measured comparison would need ceremony, and authors would strip bounds to get past it); treating `Undecided` as `False` (an unsafe default for clearance checks).

An author who wants the estimate states it: `if body.volume().estimate() > 1cm3 { … }` compiles, and the language service marks `.estimate()` as discarding a bound.

### Approximate values as inputs

Geometry is often driven by measured geometry, as in `rect(other.edge(longest).length(), 10mm)`. A feature or operation parameter of type `T` therefore accepts an `Approx<T>` when its guarantee is `Guaranteed`, which measurements of exact geometry are. The call uses the estimate, and the bound is recorded in the call's accumulator and added to the result Body's accumulated `ErrorBound` (Anvil's Body metadata). An `Estimated`, `Indicator` or `Unknown` bound fails the call with `ING6403 EstimateAsInput`, with two fixes: declare the parameter as `Approx<T>`, or write `.estimate()`. Plain `fn` parameters never coerce, so library code states which inputs may be approximate.

## Geometry in the language

### Kiln-held values

`Body`, `Part`, `Assembly`, `Instance`, `Field` and `Material` values are immutable handles to values that Kiln holds and the CAS stores. Ingot code never sees their internals; it calls operations and std features that return new handles. Copying a handle copies a reference, and equality of handles is equality of content (`ObjectId`).

| Type | Created by | Key methods (std) |
| --- | --- | --- |
| `Body` | Operations and features; `+`, `-`, `&` | `faces`, `edges`, `vertices`, `regions`, `aspects`, `volume`, `area`, `bbox`, `mass_properties`, `convert(into:)` |
| `Part` | `part(body, name:, item:)` | Fields `.body` and `.material`; methods `.material(m)` (a copy with the material set), `.tolerance(target, control)`, `.require(…)`, `.csys(name)`. A property read on an unassigned material fails with `ING6701 MaterialUnassigned` |
| `Assembly` | `assembly(instances, mates:)` | `.instances()`, `.find(path)`, `.bom()`, `.interference()` |
| `Instance` | `instance(part_or_assembly, at:, fixed:, flexible:, repr:)` | `.part`, `.placement`, `.csys(name)`, `.path` |
| `Field<Domain, V, A…>` | Flux operations and std physics | Defined by FLX |

On Bodies, `a + b` is union, `a - b` is difference and `a & b` is intersection; the right operand may also be a list of Bodies. A chain such as `a + b + c` lowers to one n-ary `anvil::boolean` call by a fixed syntactic rule of the edition, never by an optimization, so the same source always produces the same operation graph. Representations mix freely, as Anvil's representation lattice decides; `body.convert(into: Mesh, tolerance: 0.01mm)` returns `Approx<Body>`, because every conversion carries an `ErrorBound` (contract section 5).

The prelude defines the world frame: `origin`; the directions `x`, `y` and `z`, so `+z` and `-y` read naturally; the axes `x_axis`, `y_axis` and `z_axis`; and the planes `plane.xy`, `plane.yz` and `plane.xz`. A `Transform` is a rigid motion or, where an operation accepts it, a uniform or anisotropic scale; it composes with `*` and applies with `.moved(by:)`.

### Entities and call sites

An `Entity<K>` is one resolved entity: a Body's `ObjectId` and an `EntityId`. It is valid only together with its Body, and it never outlives a rebuild as an index. Accessors measure it and return `Approx` values: `e.area()`, `e.length()`, `e.normal(at: p)`, `e.radius()`, `e.surface_kind()`.

Anvil names entities by the call site of the operation that created them (D-ANV-14): "the stable syntax-node identity that Ingot assigns to each call". Ingot defines that identity.

| Part of `OpSite` | Ingot's definition | Stable under |
| --- | --- | --- |
| Statement identity | The `BlockId` of the enclosing statement block in the live document (Kiln D-KLN-22) | Edits elsewhere, moves, reformatting, literal edits |
| Call path | The path from the statement root to the call in the typed syntax tree, as slot names (`pipe.rhs`, `arg(t)`, `receiver`); a positional argument is named by the parameter it binds to | Adding or reordering arguments, editing literals |
| Feature instance path | The `OpSite`s of the enclosing feature calls, outermost first | Edits inside other features |
| Loop indices | The iteration index, or the key of a `keyed` collection | Edits that keep the iteration set |

A file outside any repository, such as a REPL cell, gets `BlockId`s derived from item paths and statement ordinals, and the language service warns that its entity names are stable only until the next edit. A file edited outside Crucible passes through Kiln's reconcile step on import, which matches blocks by GumTree, so most `BlockId`s survive.

Every query in source is re-resolved from its anchors in each build, so a changed `BlockId` never breaks a query. It costs cache reuse for the affected calls, and it moves anchors stored outside the program, such as review comments on entities, which then re-attach through Kiln's diff or report that they are stale.

`for x in keyed(holes, by: |h| h.label) { … }` uses the key in place of the index, so inserting a hole at the front of the list renames nothing. Ingot never derives a site from evaluation order, argument values or source offsets.

### The query language

A `Query<K>` describes a selection of entities of kind `K` on a subject Body and is re-resolved wherever it is used. A query is built by methods on a Body, a Part, an Instance or another query. `Query<Point>` selects points, which may be vertices or points derived from geometry, such as `face.corners(inset:)`, a circle's center or an explicit `point(…)`; points derived from geometry resolve as positions with a provenance anchor, so `hole(at:)` can follow them.

| Element | Syntax | Meaning |
| --- | --- | --- |
| Subject and cardinality | `b.face(…)`, `b.faces(…)`, also `edge`, `edges`, `vertex`, `vertices`, `region`, `regions`, `aspect`, `aspects` | Singular forms need exactly one match; plural forms need at least one, unless `count:` says otherwise (`count: 0..`, `count: 4`) |
| Anchor by provenance | `part.face(base.face(role: end_cap))` | Entities of the subject descended from the anchor, through Anvil's lineage |
| Role | `role: end_cap`, `role: side(e)`, `role: wall` | Entities created with that role (MEC D-MEC-1). Roles are constants of type `Role`, declared by the creating feature with `#[roles(start_cap, end_cap, side(Edge))]`; the prelude re-exports the common ones. A role's identity is its fully qualified path, which Anvil hashes into `EntityId`s |
| Creator | `created_by: holes` | Entities created by the operations at the call site that produced the value `holes` |
| History selectors | `new`, `modified`, `all` | Created by the subject's last operation and present in none of its inputs; modified by it; everything. The subject's last operation is the one that produced the value the query is built on, so `body.edges(new)` refers to the operation that produced `body` even after later operations |
| Geometric filters | `normal: +z`, `kind: Cylinder`, `area: 100mm2..`, `radius: 3mm ± 0.01mm`, `parallel_to: axis`, `coaxial_with: q`, `convexity: Concave`, `within: region_body` | Certified predicates evaluated by Anvil; a range or `Tol` argument means membership |
| Topology | `.edges()` of a face query, `.faces()` of an edge query, `adjacent_to: q`, `bounded_by: q` | Adjacency in the subject's topology |
| Selection | `longest`, `shortest`, `largest`, `smallest`, `nearest: p`, `first(along: d)`, `last(along: d)` | Extremal choice under certified comparison. Several selectors apply in order, each breaking the ties the previous one left. Plural forms keep remaining ties; singular forms fail on a tie with `ResolveError::Ambiguous` |
| Set algebra | `q1 + q2`, `q1 - q2`, `q1 & q2` | Union, difference and intersection of selections on one subject |
| Custom filter | `where: \|f\| f.area() > 2 * hole_area` | An Ingot predicate over each candidate `Entity<K>`; a `Truth` of `Undecided` makes the resolution fail with `Ambiguous` |
| Merge policy | `on_merge: Fail` | Fail instead of accepting a merged anchor with a note (Anvil default: accept) |

Filters are arguments, not code: `area: 100mm2..` lowers to a certified interval test that Anvil evaluates, while `where:` runs Ingot over Anvil's measurements and inherits their bounds through `Truth`. A geometric filter near its threshold is decided by Anvil's certified rule or fails with `ResolveError::Ambiguous { entity, predicate, margin }`; it never flips on rounding noise.

```
let top    = body.face(role: end_cap, created_by: base)            // provenance first
let bores  = body.faces(kind: Cylinder, radius: 3mm ± 0.05mm, created_by: holes)
let rim    = top.edges() - top.edges(adjacent_to: bores)          // set algebra
let lip    = body.edge(created_by: base, role: side(any), last(along: +z))
let blends = body.faces(new)                                       // what the last operation created
let big    = body.faces(where: |f| f.area() > 0.25 * top.area())  // custom filter, three-valued
```

A query resolves on the Body of the operation that consumes it. When a query built on `base` reaches an operation acting on `solid`, its selection on `base` becomes the anchor and maps to `solid` through lineage, which is how `fillet(solid, base.face(role: end_cap).edges())` and MEC's `hole(at: block.face(role: end_cap).corners(…))` work. A `Query` parameter of an operation or feature resolves on the first `Body` or `Part` parameter, using a Part's Body, unless `#[on(param)]` names another. If the consuming Body does not descend from the query's Body, resolution fails with `Deleted` or `NoMatch` and names both Bodies.

Resolution follows Anvil's three stages: anchor, lineage, then filter and select (D-ANV-15). Ingot lowers each query to a canonical `QueryPlan` and evaluates it as a separate Kiln node, `anvil::resolve@v(plan, body)`, before the operation that consumes it. Resolution therefore caches on its own, and an edit that leaves a selection unchanged stops propagating at the resolve node.

| Outcome | What Ingot does |
| --- | --- |
| `Resolved { entities, notes }` | Passes sorted `EntityId`s to the operation; notes appear on the query's span |
| `ResolveError::Split`, `Deleted`, `NoMatch`, `TooMany`, `Ambiguous` | A failure at the query's source span, carrying Anvil's ranked fixes as `SourcePatch`s (see "Errors, failures and checks") |

A query resolves only inside a feature body, where its consuming Body is known. It resolves when passed to an operation or feature, when code calls `.resolve()`, which returns `[Entity<K>]` in canonical order, or when code measures it, as in `top.area()`. A measurement over a plural query returns one value per entity or a reduction such as `.total_area()`; a singular query measures its one entity.

Code cannot index entities by position, and the language has no `faces()[3]`. `body.faces(…).sorted_by(|f| f.centroid().z)` returns a `[Entity<Face>]` in a stated order, and its entities convert back to queries with `e.query()`, which anchors on their `EntityId`s. The language service flags any query anchored only on an `Ordinal` discriminator, which Anvil marks fragile.

**Decision D-ING-8:** Queries are values built from named arguments and resolved by a separate `anvil::resolve` operation; geometric predicates are declarative ranges that Anvil certifies, and arbitrary predicates are an explicit `where:` closure whose undecided outcomes fail. *Why:* declarative filters can be certified, cached and explained in a `ResolveError`; separating resolution from the consuming operation gives early cutoff on selections; banning positional indexing removes the topological naming failures that index-based selection causes. *Rejected:* string selectors such as CadQuery's `">Z"` (untyped and unchecked); build123d-style sorting and slicing as the main mechanism (positional, so selections change when dimensions change); arbitrary lambdas as the only filter (opaque to certification and explanation).

### Builder blocks

A call may end with a block: `sketch(plane.xy) { rect(width, 40mm) }`. The block is a builder block, the mechanism Swift result builders introduced: each statement's value is collected into the builder's result. Ingot's rule is smaller than Swift's.

1. A function opts in with a final parameter of type `Builder<I, Ctx>`: `I` is the item type and `Ctx` the receiver whose fields and methods are in scope inside the block.
2. Each expression statement whose type implements `Emit<I>` contributes its items, in source order: an entity, a constraint, or a helper such as `rect` that emits four lines and their constraints. An expression statement of another type is an error (`ING2301`), as unused values are everywhere in Ingot.
3. A `let` binding whose value implements `Emit<I>` contributes its items and also names them. The name becomes a field of the builder's result, so `s.c` reaches circle `c` of sketch `s`.
4. `if` without `else` contributes zero or one set of items, `if`-`else` and `match` contribute one branch, and `for` contributes every iteration's items.
5. Receiver members take precedence over prelude names, so `x_axis` inside a sketch block is the sketch's own axis. A name that is both a receiver member and a binding of the enclosing code is an error (`ING1104`), with fixes to qualify it (`ctx.origin`) or rename the binding, so a receiver name never shadows a user's binding silently.

The builder receives the items, the named bindings and the receiver, and returns an ordinary value. The type of a sketch block with `let r = rect(…)` and `let c = circle(…)` is `Sketch<{ r: Rect, c: Circle }>`, a sketch whose named entities are typed fields. A signature that says only `Sketch` means `Sketch<{}>`: callers reach its entities by query, not by name. ELX's `circuit { … }` uses the same mechanism, with set-like accumulation of `connect` items.

### Sketches and constraints

MEC owns the sketch entities, constraints and solver policy; Anvil owns `anvil::solve_constraints`. Ingot supplies the block, symbolic values and the staging rule.

Inside a sketch block, entities are symbolic: `line(p0, p1)` creates two unknown points with seed values `p0` and `p1`, identified by the call site. Accessors such as `a.length` or `r.width` return `Expr<Length>`, symbolic expressions over the unknowns. Constraints are items: `horizontal(a)`, `dim(a.length, 40mm)`, `coincident(b.end, origin)`. Comparing symbolic expressions builds an equation: `e1 == e2` has type `Equation`, the same mechanism Flux uses for weak forms, so `chord_ratio(a, 0.5) == 0mm` is a constraint.

```
/// A symmetric slot centered on the origin.
pub feature slot(length: Length in 1mm.., width: Length in 0.5mm..) -> Sketch {
    sketch(plane.xy) {
        let top = line(point(-10mm, 3mm), point(10mm, 3mm))           // seeds
        let bot = line(point(-10mm, -3mm), point(10mm, -3mm))
        let r   = arc(tangent_to: top, end: bot.end)
        let l   = arc(tangent_to: bot, end: top.start)
        horizontal(top)
        symmetric(top, bot, about: x_axis)                              // receiver name
        point_on(r.center, x_axis)
        symmetric(r.center, l.center, about: y_axis)
        dim(distance(r.center, l.center), length - width)
        dim(r.radius, width / 2)
    }
}

/// A custom constraint: an ordinary function over symbolic values.
pub fn chord_ratio(a: Arc, k: Real) -> Expr<Length> {
    a.chord_length - k * 2 * a.radius
}
// inside another sketch block:  chord_ratio(fan, 0.8) == 0mm   (an Equation item)
```

Branching on a symbolic value is a type error: `if a.length > 5mm` fails with `ING2402`, because `Expr<Bool>` is not `Bool`. Conditional residuals use `select(cond, x, y)`, which Anvil's solver and Flux's kernel compiler both understand. Seeds are ordinary literals: a drag in the sketch editor rewrites them on release, as the UIX tab specifies, and a build never warm-starts from a previous solve (MEC).

The sketch block must express real-world sketches, not only textbook ones. SketchGraphs provides "15 million sketches extracted from real-world CAD models", each "represented as a geometric constraint graph"; oracle ING-O-23 converts a fixed sample into Ingot sketch blocks and requires every constraint type to have an Ingot form and every converted sketch to re-solve to the recorded geometry.

The block evaluates strictly to a constraint system: unknowns with seeds, residual expression DAGs and driving values. `anvil::solve_constraints@v` then solves it as one operation node. The returned `Sketch` is a Body (wires and planar regions) plus the solve report. Reading `s.c.center` after the solve returns `Approx<Point3>`, whose bound comes from the solver's converged residual.

**Decision D-ING-9:** Constraints, analytic Field expressions and weak forms are one mechanism: staged symbolic values (`Expr<T>`, `Equation`, Flux's form types), built by ordinary Ingot functions and handed to the consuming operation as a hash-consed expression DAG, which Flux's kernel compiler lowers and differentiates. *Why:* one mechanism serves MEC's custom constraints, FLX's constitutive functions and boundary data, and analytic Fields; any pure Ingot function works on symbolic values without a restricted dialect; hash-consing makes equal expressions equal keys in Kiln. *Rejected:* a `constraint` keyword with its own differentiable subset, as MEC drafted (a second function kind for one client); tracing arbitrary Ingot code into the kernel IR (branches on unknowns would be captured silently for one value).

### Assemblies and interfaces

An Instance's path is the list of instance names from the root assembly, such as `drive/wheel`. A query through an Instance, such as `wheel.face(role: bore)`, resolves on the Part's Body and carries the Instance's placement, so measurements between Instances are in assembly coordinates. Mates take `CoordSys` values, which re-resolve through their anchor queries (MEC). Parameters flow into an assembly as ordinary arguments of the assembly feature, as worked example 2 shows; there is no global variable table.

A cross-part interface, MEC's D-MEC-13, is an ordinary record marked `#[interface]`, which derives a `compatible(a, b)` check over its fields. No `interface` keyword is needed.

### Patterns, loops and identity

MEC defines `pattern`, `linear`, `circular`, `along`, `fill` and `by_density` (D-MEC-8). Ingot supplies two guarantees they rely on. First, a pattern is a feature whose instances differ only in the loop index or key inside their `OpSite`. Second, a `for` loop is an expression that yields a list, so per-instance variation is ordinary code.

```
let vents  = pattern(vent_slot(length: 10mm), at: linear(dir: +x, count: 8, spacing: 6mm))
let graded = for i in 0..8 { vent_slot(length: 10mm + i * 2mm) |> move(x: i * 6mm) }
let cover  = blank - vents - graded                    // graded is [Body]; one n-ary difference
```

`for` loops iterate finite lists, ranges, maps and keyed collections, and each iteration runs in its own scope. There is no mutable accumulator; `fold(xs, init, f)` and `scan` cover running state. A loop over a range of quantities needs an explicit step.

### Configurations, design tables and families

A feature's parameter list is a record type, written `Params<f>`. Its fields have the parameters' types and defaults, so a literal of type `Params<bracket>` may omit defaulted fields, and a field of type `T` accepts a `Tol<T>` exactly as the parameter does. A call spreads a record into named arguments: `bracket(..heavy)`. These two rules implement MEC's D-MEC-10: a configuration is a parameter record, a design table is a table of parameter records, and suppression is a `Bool` parameter used in an `if`.

```
let heavy: Params<bracket> = { width: 80mm, thickness: 5mm ± 0.1mm, load: 2kN }
let b = bracket(..heavy, width: 90mm)                  // later arguments override the spread

pub let brackets = family(bracket, key: |r| r.item, rows: table {
    item     | width | thickness     | load
    "BR-060" | 60mm  | 4mm ± 0.1mm   | 1.2kN
    "BR-080" | 80mm  | 5mm ± 0.1mm   | 2kN
})
pub let more = family(bracket, key: |r| r.item, rows: table("brackets.csv"))
```

A table literal has a header row of field names and one row per line, separated by `|`. Its row type is `{ item: String, ..Params<bracket> }`, a record spread as described under "Records, enums and tagged unions" (`ING2105` when a shared field has a different type). Every cell is type-checked against its column; a cell may be any expression, but every dimensional cell carries its unit.

`table("brackets.csv")` reads a CSV file stored in the design repository. The file is a source input of the compilation unit, like an `.ingot` file, so reading it is not IO. Its header names columns and units, as in `item, width [mm], thickness [mm], load [kN]`. Cells hold numbers in the header's unit, and a cell such as `4 ± 0.1` is a tolerance in that unit. The front end checks headers and cells at compile time and reports `ING3501 UnitMismatch { column, expected }` with the cell's file position.

The formatter aligns table columns, and the structural editor treats each row as a block, so two people adding rows concurrently merge cleanly.

## Effects, purity and determinism

### Kinds of calls

Every Ingot call is pure. Calls differ in cost and in whether Kiln memoizes them, and the kind of a call is visible in its declaration. A `feature` may return any type, including records of geometry and plain values, as skeletons and interfaces need (MEC); a feature is the unit of history and of caching, and a `fn` is not.

| Call kind | Declared with | Kiln node | Example |
| --- | --- | --- | --- |
| Function | `fn` | No; compiled code calls it directly | `rms(xs)`, `fit(10mm, H7)` |
| Memoized function | `#[memo] fn` | Node keyed by code hash and arguments only, not shown in history; it may not call operations or features (`ING2501`), so results are shared across call sites | An expensive table interpolation |
| Feature | `feature` | Feature node; the unit of history | `bracket(width: 60mm)`, `fillet(b, e, 2mm)` |
| Operation | `extern fn` with `#[op("anvil::blend")]` | Op node, keyed by `OpKey` | Called inside std `fillet` |
| Wasm component export | `extern fn` with `#[component(…)]` | Op node whose `impl` is the component | `solve_raw` in worked example 5 |
| Query resolution | Implicit, where a `Query` reaches an operation | Resolve node | `body.faces(new)` |
| Check | `require` | Check node | `require stress < limit` |

Operations and Wasm component exports are the engine effects: the only way Ingot reaches native or sandboxed code. They are pure in meaning and expensive in cost, so Kiln runs them asynchronously, caches them and shares them. `extern` declarations are ordinary public items. `ingot-bindgen` generates `std::ops::anvil` and `std::ops::flux` from the engine's operation catalog, and any package may declare its own, so std has no private door (principle 1). The compiler checks every `#[op]` declaration against the catalog signature (`ING8001`).

Ingot source never names a behavior version. The design's lockfile pins one behavior version per operation, and Kiln dispatches each call to it (D-KLN-4). Writing `anvil::blend@2` remains a documentation convention.

**Decision D-ING-10:** Ingot has no user-visible effect system. Purity is total, operations are pure calls, and the side channels that exist (checks, notes, tolerance sites, PMI) are write-only accumulators ordered canonically by call site, in the manner of Salsa's accumulators, which carry side-channel data such as diagnostics apart from a function's return value. *Why:* effect annotations would add a concept to every signature to describe effects the language does not permit; canonical ordering makes the accumulators independent of evaluation order and parallelism. *Rejected:* an effect-row type system (no effects to track); monadic sequencing of operation calls as in FeatureScript's `context` and `id` threading (boilerplate that encodes an order the dataflow already determines).

### Determinism guarantees

Same source, lockfile and input cells give the same values, failures and fuel counts on every engine and every Tier 1 target. The rules below make that hold.

| Source of variation | Ingot rule |
| --- | --- |
| Evaluation order | Defined: strict, left to right. Parallel execution is never observable, and failures are reported in program order (see "Evaluation semantics"). |
| Floating point | Binary64 basic operations, correctly rounded. The compiler never contracts `a*b + c` into a fused multiply-add and never reassociates; `fma(a, b, c)` is explicit. Elementary functions come from the Platform tab's correctly rounded `detmath` (D-KLN-11), ported from or equivalent to CORE-MATH, an MIT-licensed project that provides "mathematical functions with correct rounding". |
| NaN and infinities | Not values. The operation that would first produce one fails with `ING6102 NumericError`, naming the operation and its operands. |
| Integers | 64-bit, checked; overflow fails with `ING6101`. |
| Collections | Maps and sets are ordered by key. Sorts are stable, and ties fall back to the canonical order of the elements. |
| Map keys | `Real` and quantities are not keys; `q.key(resolution: 1um)` quantizes explicitly. |
| Strings | NFC, compared by code point; no locale anywhere. Numbers print as the shortest decimal that round-trips. |
| Randomness | Only explicit `Rng` values (below). |
| Time, environment, files, network | Not exposed. Source files, CSV tables, Assets, Materials, catalog records and External inputs are Kiln input cells, read by content. |
| Resource limits | Counted in deterministic units, never in wall time (below). |
| Kiln-held values | Handles compare by content identity (`ObjectId`). |
| Machine code | Generated WebAssembly uses no relaxed SIMD, threads or shared memory, never depends on `memory.grow` failing, and never lets a NaN be observed. Every conforming engine therefore computes the same results (see "Compilation strategy"). |

### Explicit randomness

Randomness is a value. `Rng` is a key for Philox, the counter-based generator of Salmon and colleagues, in its 4×32 form with 10 rounds [unverified: variant and round count are from the paper body, which was not checked]. Counter-based generators turn "independent, keyed transformations of counters" into random streams, need no mutable state and pass TestU01's BigCrush. Because the n-th number is a pure function of the key and n, a stream can be indexed, split and consumed in parallel without changing any value.

```
pub feature scatter_pins(region: Query<Face>, count: Int in 1..=10_000, seed: Seed = Seed(7)) -> [Point3] {
    let rng = Rng::new(seed).split("pins")          // a child key, derived by hashing the label
    let u = rng.uniforms(count, of: 0.0..1.0)        // the first `count` numbers of this stream
    let v = rng.split("v").uniforms(count, of: 0.0..1.0)
    region.sample_at(zip(u, v))                      // deterministic on every engine
}
```

A seed is an explicit parameter, never ambient. std's sampling functions (`sobol(dim, n, scramble: rng)`, `latin_hypercube`, `normal`) take an `Rng` argument. MEC's D-MEC-22 derives scramble seeds from `EntityId`s, which `Seed::from(entities)` supports. `rng.seed()` derives a 64-bit `Seed` for a Wasm component, which ECO's solver world receives as `seed: u64`.

### Resource limits

Every evaluation ends in a value or a typed failure, because each limit below is counted in units that the language defines.

| Limit | Unit | Default per feature call | Failure |
| --- | --- | --- | --- |
| Fuel | Steps of the language's cost table | 10⁹ steps; `#[fuel(…)]` raises it up to the manifest maximum and the organization ceiling | `ING6301 FuelExhausted { used, limit }` |
| Call depth | Ingot frames | 2,048 | `ING6302 DepthExhausted` |
| Memory | Semantic bytes: 8 per scalar or handle, 16 per collection header plus its elements | 1 GiB | `ING6303 MemoryLimit` |
| Operation calls | Count | 10⁶ | `ING6304 TooManyOperations` |
| Symbolic expression size | DAG nodes | 10⁷ | `ING6305 ExpressionTooLarge` |

The cost table belongs to the language behavior version, so a cost change is a pinned behavior change, never a silent one. Limits apply per feature call. A call's own steps count against its limit, including the plain functions it calls. Feature calls and `#[memo]` function calls are Kiln nodes with their own limits, so they do not count against the caller. A feature call's outcome therefore never depends on its caller's remaining budget or on what happened to be cached. Termination still holds, because every call is bounded and call depth is bounded. An operation call charges a fixed 100 steps plus 1 step per argument element marshalled; its internal work is bounded by its own deterministic budget (Anvil, Flux).

Ingot fuel and Wasm component fuel are separate budgets in separate units. Ingot fuel counts language steps under the language behavior version's cost table; component fuel counts instructions under PLT's `instrument@N` cost table. Both are deterministic.

When the host cannot supply memory below the semantic limit, evaluation fails with an environmental `ResourceExhausted`, which Kiln never caches (D-KLN-6). Wall-clock limits exist only as cancellation, which returns no result rather than a different one.

## Evaluation semantics

### Strict, ordered, and failure-aware

Evaluation is call by value. Arguments evaluate left to right, then the call runs; statements run in order; the last expression of a block is its value. A module-level `let` is evaluated on demand as a Kiln node with no parameters, and module-level bindings may not depend on each other cyclically (`ING1302`). There is no laziness in the language, with two deliberate exceptions: `require` predicates and the arms of `if` and `match` that are not taken.

A failure is a typed value describing why a computation could not produce its result. A failing call aborts the enclosing expression, and the failure propagates outward to the nearest `try` or to the enclosing feature call. The feature's result then is that failure, which Kiln caches like any value (D-KLN-6). `try e` turns propagation into a value of type `Result<T, Failure>`.

```
let rounded = match try body |> fillet(edges, r) {
    ok(b) => b,
    err(BlendError::RadiusTooLarge { max }) => body |> fillet(edges, 0.95 * max),
    err(e) => fail(e),
}
```

`Failure` is an extensible union, like OCaml's extensible variant types [unverified: OCaml manual not opened]. Every enum that implements `Error` adds its variants; patterns over a `Failure` name those variants directly; a match over `Failure` needs a wildcard arm. Anvil's `OpError` and `ResolveError`, MEC's `FeatureError`, Flux's solver errors and user-defined errors all take part.

**Decision D-ING-11:** Failures propagate automatically to the nearest `try` or feature boundary and become ordinary cached values there; `try` converts them into `Result` for recovery. `Result` and `?` remain for conditions a library chooses to return. *Why:* operations fail routinely (a fillet radius too large, a query split), and forcing `?` onto every geometry call would add noise to nearly every line while adding no information, because every failure already carries its code, location and fixes. *Rejected:* `Result` on every operation with mandatory `?` (noise); untyped exceptions (recovery code could not match on causes); silent fallbacks (the contract forbids them).

A feature's checks are evaluated against its result. When the feature fails, its checks report `Error(DependencyFailed)`, never `Pass`.

Failure inside one Instance of an assembly does not erase sibling work. Every node that evaluated keeps its value, and the UI shows them all. A node that needs a failed value fails with `DependencyFailed { upstream }`, which points to the original failure.

### Suppression and rollback

`#[suppressed]` on a `let` statement removes the call from evaluation, and the feature tree shows it greyed. For a pipeline statement whose input and output types agree, as in `let s = body |> fillet(…)`, the binding takes the pipeline input, so `s = body`. This matches what CAD users expect from suppressing a modifying feature. For any other statement, every use of the binding fails with `ING6601 Suppressed { binding }` and the UI marks the dependents. Suppression controlled by a parameter is an ordinary `if`, as MEC's D-MEC-10 decides.

Rollback evaluates a feature body up to a chosen statement and returns that statement's binding. It is an evaluation request, `EvalRequest { target, until: BlockId }`, and never a source edit, so it serves the history panel and the debugger alike.

### The Ingot IR

Lowering produces the Ingot IR (IIR), a dataflow graph in the style of the regionalized value state dependence graph (RVSDG): "a data flow centric IR where nodes represent computations" and "regions capture the hierarchical structure of programs". Ingot is pure, so the IIR needs no state edges.

| IIR construct | Meaning |
| --- | --- |
| Simple node | Arithmetic, record and collection construction, field access, unit-free numeric code |
| Kiln call node | A call that compiled code hands to Kiln: an Op (an operation, a Wasm component export or a query resolution), a feature call or a check registration, with its `OpSite` |
| γ region | A conditional, with one sub-region per branch |
| Map and fold regions | `for` loops and folds, whose iterations carry their index or key into `OpSite` |
| λ and φ regions | Functions and recursive groups |
| Observation edge | Marks where compiled code needs the content of a Kiln-held value: a measurement, a branch on a computed value, `try` |

The IIR excludes source positions, comments and documentation. Spans live in a side table keyed by syntax-node identity, so an edit above a function leaves that function's IIR, and therefore its cache keys, unchanged. Each item gets a code hash: a SHA-256 Merkle hash over its IIR and the code hashes of the items it calls. Feature keys use it, so a change to one function invalidates exactly the features that can reach it.

### The incremental contract with Kiln

Ingot runs inside Kiln's demand-driven graph. The front end, compiled code and Kiln call nodes divide the work as follows.

1. **Front-end nodes.** Kiln keys each module's front-end node by module identity and the Ingot compiler behavior version (KLN graph model). Stages run as separate memoized queries: parse, item table, signatures, bodies, IIR, Wasm. Signatures are required, so editing a body re-checks that body only, and dependents re-check only if a signature changed. Each stage backdates when its output is unchanged, so a comment edit stops at the IIR.
2. **Feature nodes.** A feature call is a node keyed by the feature's code hash, its `OpSite`, the arguments' `ObjectId`s, the operation version pins and the package closure that Kiln names (D-KLN-3). The code hash is the finer part of that closure, and the `OpSite` is needed because entity names depend on it. A closure argument is keyed by its code hash and the canonical encodings of its captured values. Its value is the result or failure, plus accumulators and recorded fuel.
3. **Asynchronous Kiln calls.** Compiled code issues each operation, resolve and feature call to Kiln and receives a pending handle at once. It suspends only at observation edges. Independent calls in a body therefore run in parallel without annotations, as Kiln's suspending scheduler expects (D-KLN-1).
4. **Static prefetch.** For each feature body, the IIR lists the Kiln call nodes whose inputs are known before any observation. Kiln uses the list to prefetch across suspension points, and the list is a sound under-approximation of what compiled code issues.
5. **Program order.** Every Kiln call records its program-order index within the feature call. When several calls fail, or fuel runs out while calls are pending, the outcome is the earliest event in program order. Speculative work after that point is discarded and never changes a result.
6. **Overrides.** An evaluation request may carry literal overrides, `{ LiteralSite => Value }`, where a `LiteralSite` is a `BlockId` plus the literal's call path. Kiln treats them as input cells, so a drag evaluates new values without editing source or creating Changes (UIX D-UIX-15). An override must have the literal's type and dimension, or the request fails with `ING6502`.

[[DIAGRAM: Ingot pipeline. Left column "Front end (Kiln front-end nodes)": source text → lossless syntax tree (green/red) → typed AST with spans → name resolution and type check (units, tolerances, kinds) → IIR (RVSDG-style; spans in side table) → code hash per item. Middle column "Code": IIR → optimizer (no reassociation, no contraction, fuel totals preserved) → Wasm module + source map → cached in CAS; reference interpreter beside it with a dashed "differential oracle" arrow. Right column "Execution (Kiln)": compiled feature body → issues Kiln calls (Op, resolve, feature, check) as pending handles → Kiln schedules Op nodes (Anvil, Flux, Wasm components) → values flow back at observation points → feature value + accumulators (checks, notes, tolerance sites) + recorded fuel. Bottom arrows: "literal overrides (drag)" into execution; "BlockId + call path → OpSite" from the syntax tree into Kiln calls.]]

### Previews, drags and incomplete code

Three mechanisms keep evaluation responsive while people and agents edit.

| Mechanism | What it does | Contract |
| --- | --- | --- |
| Fidelity context | A request names `Preview`, `Interactive` or `SignOff`; operations receive it in their `OpKey` | Ingot code cannot observe fidelity, so every fidelity runs the same program. Preview results carry `Estimated` bounds and a `Preview` flag, so a branch on them may stop with `UndecidedBranch` where the exact build would decide. A check's own `fidelity:` field names the fidelity of the Kiln check node that evaluates it, so a release evaluates sign-off checks even when geometry ran interactively. |
| Drag specialization | When a drag starts on a literal, Ingot partially evaluates the program: it computes the forward slice of that literal in the IIR and compiles a residual program in which everything outside the slice is a constant taken from the current evaluation | Each frame re-runs only the slice. The residual program is an optimization: its outputs equal the full program's on the same override (oracle `ING-O-12`). |
| Holes | The error-resilient parser turns an unfinished expression into a typed hole. Evaluation proceeds around holes, as in Hazel's live semantics, where "evaluation proceeds around holes, tracking the closure around each hole instance" | A hole evaluates to the failure `ING6001 Incomplete`, so code that does not depend on it keeps evaluating and the viewport stays live while someone types. |

### Derivatives

The UIX tab ranks direct-manipulation edits by the derivative of a dragged quantity with respect to each contributing literal (D-UIX-15), and Flux exposes `grad(J, wrt: [p1, p2])`. Ingot supplies both from one mechanism.

1. **Dependence.** The IIR's data dependence plus provenance (which `OpSite` created an entity) gives the set of literals that can affect an entity. This is exact, cheap and always available.
2. **Forward-mode differentiation.** `ingot-ir` differentiates compiled code by dual numbers. At Kiln call nodes it calls the operation's tangent rule: Flux registers tangent and adjoint rules for its operations, and Anvil supplies shape derivatives through `anvil::shape_velocity`.
3. **Reverse mode.** `grad` over many parameters uses Kiln's reverse traversal of the Op graph (FLX interfaces), with Ingot's reverse rules for the code between operations.

An Op without a tangent rule makes the derivative fail with `NotDifferentiable { op }`, and the UIX ranking falls back to dependence only. Ingot never substitutes finite differences silently; `fd_grad(…, step:)` exists as an explicit, labelled estimate.

## Errors, diagnostics and checks

### Diagnostics

Compile-time diagnostics and evaluation failures share one structure, so the UI, the CLI and agents handle them alike.

```rust
pub struct Diagnostic {
    pub code: Code,                       // "ING3001"; other subsystems use their own prefixes
    pub severity: DiagnosticSeverity,     // Error | Warning | Info | Hint
    pub message: String,                  // one sentence: what is wrong and why
    pub primary: SourceSpan,
    pub labels: Vec<(SourceSpan, String)>,// secondary spans, such as the other operand's declaration
    pub notes: Vec<String>,               // the rule, with a link to the generated catalog page
    pub fixes: Vec<Fix>,                  // ranked
}

pub struct Fix {
    pub title: String,                    // "Convert load to a length with a spring rate"
    pub edits: Vec<SourcePatch>,           // minimal edits on the lossless tree
    pub applicability: Applicability,     // MachineApplicable | MaybeIncorrect | HasPlaceholders
    pub stability: Option<Stability>,     // for query fixes: resolutions identical under 16 perturbations (D-AGT-8)
}

pub struct SourcePatch {                  // the same record AGT returns from edit.apply
    pub path: SourcePath,
    pub range: TextRange,
    pub expected: Sha256,                 // of the replaced text, as AGT's `Edit::Patch` requires
    pub replacement: String,
}
```

| Code range | Area | Examples |
| --- | --- | --- |
| ING0xxx | Lexing and parsing | `ING0002` non-NFC source; `ING0101` unterminated block comment |
| ING1xxx | Names, modules, visibility | `ING1001` unknown name, with nearest names; `ING1104` builder name clash |
| ING2xxx | Types and traits | `ING2001` type mismatch; `ING2105` overlapping record spread; `ING2402` branch on a symbolic value |
| ING3xxx | Units, dimensions, kinds | `ING3001` incompatible dimensions; `ING3002` incompatible kinds; `ING3201` affine misuse; `ING3501` CSV unit mismatch |
| ING4xxx | Tolerances and GD&T | `ING4001` inverted limits; `ING4101` comparison of tolerances; `ING4201` material condition on a non-size aspect |
| ING5xxx | Geometry references | `ING5001` positional entity access; `ING5101` query anchored only on a fragile ordinal |
| ING6xxx | Evaluation failures | `ING6001` incomplete code; `ING6301` fuel; `ING6401` undecided branch; `ING6501` parameter out of range |
| ING7xxx | Packages, versions, lockfile | `ING7001` unresolvable dependency, with PubGrub's explanation; `ING7201` values crossing two major versions |
| ING8xxx | Bindings and components | `ING8001` extern signature differs from the catalog; `ING8101` WIT type without an Ingot mapping |
| ING9xxx | Lints | `ING9001` naming; `ING9101` discarded bound via `.estimate()` |

Every code has a generated catalog page with the rule, an example that triggers it and an example of each fix, all compiled in CI (AGT D-AGT-23). A fix marked `MachineApplicable` must compile and remove its diagnostic; oracle `ING-O-9` applies every such fix in the corpus and checks both.

The unit error in the contract's example reads, in full:

```
error[ING3001]: cannot add Length and Force
  --> bracket.ingot:14:17
   |
14 |     let x = width + load
   |             ----- ^ ---- Force (kg·m/s²), declared at 9:5
   |             |
   |             Length (m), declared at 7:5
   = note: + and - need operands of one dimension
   = fix (maybe incorrect): convert load to a length with a compliance: `width + load * compliance`, compliance: Quantity<T^2/M> (m/N)
   = fix (has placeholders): compare instead: `width < ?`
```

### Failures at evaluation

An evaluation failure is a `Failure` value with the same fields plus the feature call chain, the entities involved and an optional cause. Anvil's `ResolveError` fixes and MEC's `FeatureError` fixes arrive as `Fix` values with `SourcePatch`s, so a person clicks them and an agent applies them through `edit.apply` without translation.

Compiled code checks non-finite values, fuel and depth at region granularity, not per instruction. When a check fires, Kiln replays the feature call in the reference interpreter, which checks after every step and reports the exact expression. Replay reads every operation result from the cache, so it costs only interpretation of that one call, and only on the failure path.

### `require` and checks

`require` declares a check: a predicate with a severity, a fidelity, an evidence level and an oracle source. It never changes the value it is attached to, and its predicate runs as a separate Kiln check node, after the geometry it reads.

```
require stress < 0.6 * sy, severity: Error, fidelity: SignOff, evidence: Guaranteed,
        name: "static_margin", because: "allowable of 0.6 Sy for this bracket class"
part.require(part.mass() < 120g, severity: Warning)      // attaches to the Part and returns it
```

A `require` statement attaches its check to the feature call that contains it, and a `require` at module level is a design-level check over the module's public items. The method form `x.require(…)` attaches the check to `x`, so the check travels with that value. A Part keeps its checks when an assembly instances it, and the check's identity includes the Instance path, so each occurrence is reported separately.

| Field | Default | Meaning |
| --- | --- | --- |
| `severity` | `Error` | `Error` blocks merges into protected branches and releases; `Warning` and `Info` report only |
| `fidelity` | `SignOff` | The fidelity at which a release or protected merge evaluates the predicate; interactive views show interactive outcomes with their badge |
| `evidence` | `Estimated` | The weakest `ErrorBound` guarantee that may decide `Pass` or `Fail` |
| `name` | Derived from the predicate's source | Stable identity of the check across edits; Kiln's diff and merge match checks by it |
| `because` | none | Rationale shown in reports and to agents |

The outcome is `Pass`, `Fail`, `Undecided { reason, needed }`, `Error(failure)` when the predicate itself fails, or `Skipped { reason }`. This extends AGT's `CheckStatus` with `Undecided`, as FLX's CCR-FLX-3 requests (CCR-ING-1). When the predicate is a comparison chain, the check records each side as value and limit and computes the margin, so reports and review deltas need no extra code. A conjunction records one sub-outcome per conjunct.

A `require` statement inside a file under the protected `oracles/` directory gets the oracle source `Protected(path)`, which agents cannot edit and whose loosening needs human approval (contract section 7). Every other check has the source `Declared(span)`.

A waiver is a check-level attribute, `#[waive(check: "static_margin", reason: "…", until: "C")]`, on the statement that would fail. It shows in review diffs and reports, and it never suppresses `Protected` checks. ELX uses the same form for ERC waivers.

**Decision D-ING-12:** Checks are declarations evaluated as separate nodes, never inline assertions: a failing or undecided check does not stop geometry, and a feature cannot branch on a check's outcome. *Why:* designers need to see the geometry that fails a check; separate nodes let expensive predicates (simulations) run at lower priority after geometry, and keep checks out of the feature's dataflow so that adding a check never changes a design. *Rejected:* assertions that abort evaluation (hide the geometry that failed); checks as ordinary Booleans in the dataflow (a check could then alter geometry, and adding one would invalidate caches).

## Compilation strategy

Features are Ingot, so Ingot's own execution must cost little next to the operations it calls. The target is that Ingot code, excluding operations, takes at most 2% of the contract's 2 s rebuild of a 200-feature part: 40 ms, or 200 µs per feature (target). Gear tooth math, pattern layouts, tolerance tables, cost roll-ups and constraint assembly also run as plain Ingot, so plain numeric code must be fast as well.

### Options compared

| Criterion | Bytecode VM in Rust | Native code via Cranelift (JIT or AOT) | WebAssembly, run by each platform's engine |
| --- | --- | --- | --- |
| Code speed | Copy-and-patch compiled code "runs an order of magnitude faster than interpretation" (Xu and Kjolstad), which bounds what an interpreter gives up | Cranelift's output is "~2% slower than that of V8 (TurboFan), and ~14% slower than WAVM (LLVM)" | Cranelift compiles Wasm natively, so the same figures apply. Browser engines ran SPEC CPU 45% (Firefox) to 55% (Chrome) slower than native on average, with peaks of 2.08× and 2.5× (Jangda and colleagues, USENIX ATC 2019) |
| Compile latency | None | "approximately an order of magnitude faster than WAVM (LLVM)" | Same as Cranelift natively; browser baseline compilers in the browser |
| Browser | The VM compiled to wasm32: an interpreter inside an engine | Impossible: a browser cannot load native code, so a second back end is needed | Native to the platform: the browser's engine runs it |
| iPadOS (no JIT) | Works | Needs a second back end | Wasmtime's Pulley interpreter, which "will never be as fast as native Cranelift backends" |
| Determinism | Defined by one Rust implementation | Defined by the compiler on each target; two back ends must agree | Defined by one module for every engine, given the deterministic subset (below) |
| Isolation | Rust memory safety | Generated machine code runs inside the engine process; a code generator bug can corrupt it | Each module runs in its own linear memory; a code generator bug stays inside it |
| Fuel and limits | Easy | Must be compiled in | Compiled in, identical for every engine |
| Reuse | New code | Cranelift already in the build through Wasmtime | Wasmtime, its precompile cache and PLT's `wasm-host` are already required by Wasm components (D-PLT-21) |

**Decision D-ING-13:** Ingot compiles to WebAssembly core modules. Native targets compile them ahead of use with Wasmtime's Cranelift back end, and browsers run them in their own engines. A reference interpreter over the IIR is the second, conforming executor; it runs Ingot on targets without JIT, and it also runs cold code while compilation proceeds, single-steps in the debugger, replays failures and serves as the differential oracle. *Why:* one code generator produces one artifact that runs on every Tier 1 target and in every browser, so identical features need no second back end; Cranelift's code is within about 14% of LLVM's; Wasm's sandbox contains code generator bugs; and the Wasm runtime is already a dependency for Wasm components. *Rejected:* a bytecode VM as the only executor (about ten times slower than compiled code); direct native code from Cranelift (no browser path, so two back ends must agree forever); compiling Ingot to Rust (needs a Rust toolchain at run time and cannot run in a browser); LLVM (slow to compile, and cannot target the browser at run time).

### Pipeline and caching

1. The front end produces the IIR per item (see "Evaluation semantics").
2. The optimizer runs semantics-preserving passes on the IIR: inlining of small functions, constant folding, common subexpression elimination, scalar replacement of records, elimination of bounds checks, and unboxing of quantities into raw `f64`. Dimensions are already erased, so `Length` arithmetic compiles to plain `f64` instructions.
3. Code generation emits one Wasm module per compilation unit: a published package version, or a single module while it is being edited, so an edit recompiles one module. Each module carries a source map from Wasm offsets to IIR nodes and source spans.
4. Kiln caches the module in the CAS by hash(IIR, code generator version, language behavior version). Wasmtime's precompiled form is cached by PLT's key (module hash, Wasmtime version, configuration fingerprint, target, CPU features).

The optimizer obeys four rules that make it unobservable:

1. **No floating-point reassociation and no contraction.** `a*b + c` stays two rounded operations unless the source says `fma`.
2. **Failures stay.** A computation that can fail (overflow, a non-finite result, a range check) is removed only if its result is unused and it is proven not to fail; otherwise it stays where program order puts it. Loop-invariant code motion hoists only computations that cannot fail.
3. **Fuel is fixed before optimization.** Fuel costs are computed on the canonical IIR, region by region, and optimized code charges those precomputed totals. An optimization can make code faster but never changes its fuel count.
4. **Kiln calls keep their sites and program order.** Calls are never merged, duplicated or reordered in their recorded program order.

std ships precompiled for every Tier 1 target in installers and offline bundles, as PLT does for std components. User code compiles on first use. The tiering rule is fixed: a function runs in the reference interpreter until its compiled module is ready, then switches at the next feature call boundary. Both executors give identical values, failures and fuel counts, so the switch is unobservable. Target: an edited module of up to 2,000 lines compiles to a loaded native module within 50 ms on the reference laptop (target).

### The deterministic Wasm subset

The code generator emits a fixed subset of WebAssembly. It needs none of the engine settings that browsers lack, which PLT identifies as the obstacle for Wasm components (D-PLT-22).

| Concern | Rule for generated modules |
| --- | --- |
| Instructions | Core instructions, including fixed-width 128-bit SIMD; never relaxed SIMD, threads, shared memory, atomics, memory64, exception handling, garbage collection or stack switching |
| NaN | Never observable: Ingot has no float reinterpretation, and the generated code checks for a non-finite value before every comparison, branch, conversion to integer, store into a persistent value and Kiln call. A NaN's bits are therefore never seen, and the Wasm 3.0 deterministic profile's canonical NaN rule is unnecessary for Ingot code |
| Integer overflow | Checked by explicit comparisons, failing with `ING6101` |
| Float to integer | Range-checked before conversion, so the trapping conversion never traps |
| Memory | The module declares its maximum memory, and the host reserves it in its memory budget before instantiation. Generated code never inspects the result of `memory.grow`: growth either succeeds or ends the call with the environmental failure `ResourceExhausted`, which is never cached. The nondeterminism of `memory.grow` that Wasmtime's guide describes therefore never reaches a value |
| Stack | A logical depth counter in every function prologue enforces the limit in "Resource limits", set below the smallest engine stack measured on Tier 1 targets (oracle `ING-O-6`) |
| Elementary functions | From PLT's `detmath`, compiled to Wasm and linked into the module's runtime library; correct rounding makes them bit-identical to the native build |
| Fuel | Charged per region by the canonical-IIR totals, in a module global; the host reads it at every Kiln call and at exit. This is injected metering, which wasm-instrument describes as "injecting the necessary code directly into the wasm module", with costs taken from the language instead of from instructions |

Generated modules still pass PLT's validator, which rejects forbidden instructions and imports. They skip PLT's instrumentation rewrite, `instrument@1`, for a reason specific to compiled code. A component's bytes are pinned by hash, so instruction counts measure its work stably. Ingot's compiled bytes change whenever the code generator improves. Fuel must be a property of the program, not of one compiler's output, so Ingot charges language steps computed on the canonical IIR. A module that Crucible's code generator did not produce never loads as Ingot code; precompiled artifacts load only if this machine or Crucible's signing build service produced them, PLT's rule for components.

### Suspension without stack switching

Compiled code suspends where it needs a value that Kiln has not finished. WebAssembly stack switching is not available everywhere Ingot runs: Wasmtime's tier documentation lists it as still unsupported by Cranelift on aarch64, and browser support is [unverified]. Ingot therefore does not depend on it. The compiler lowers each function that may observe a pending value into a resumable state machine, the transformation Rust applies to `async` functions. The host drives it with `resume(state) -> Pending(handles) | Done(value) | Failed(failure)`. Which functions may suspend is inferred and never appears in types (D-ING-10 stays). A function that observes only ready values runs straight through.

### Values and memory

Each feature call runs in a fresh instance drawn from a pool. The modules it needs are instantiated against one shared linear memory and one imported runtime module (allocator, reference counting, `detmath`), so calls between modules are direct calls. A fresh instance per call means no state can leak from one feature call to another. Arguments and results cross the feature boundary as canonical encodings for plain values and as handles for Kiln-held values, the same encodings Kiln needs to key the call. Target: under 10 µs per instantiation from the pool (target).

Kiln-held values cross between a module and the host as 32-bit handles into a per-call handle table, never as bytes. Plain values live in the module's linear memory. Large plain values that a Kiln call needs, such as a list of 10⁶ points for `anvil::points_to_mesh`, are copied once into a host buffer and continue as handles.

**Decision D-ING-14:** Plain values in compiled code use precise reference counting with reuse analysis, the Perceus algorithm, so a functional update of a uniquely referenced list or record happens in place. *Why:* Ingot values are immutable and strict, so reference graphs are acyclic and reference counting is complete without a cycle collector; Perceus is proved "garbage free, where only live references are retained" and enables "guaranteed in-place updates at runtime"; prompt freeing keeps loops that build large collections within the semantic memory limit. *Rejected:* a tracing collector (pause times inside a drag frame, and a larger runtime in every module); one arena per feature call (simple, but keeps all intermediate garbage until the call ends, which breaks long loops); ownership types exposed to users (too much ceremony for design code).

Memory accounting for limits uses semantic sizes, so the allocator's behavior never affects whether a limit is hit.

### Identical behavior everywhere

| Target | Executor | Notes |
| --- | --- | --- |
| Windows, macOS, Linux on x86-64 and ARM64; servers | Wasmtime with Cranelift through `wasm-host` | Precompiled std; user modules compiled on first use and cached |
| Desktop browsers | The browser's own Wasm engine in the engine worker | Ingot modules are core modules, not components, so they need none of jco's component transpilation. The module imports host functions from the engine's own Wasm build. The page's Content Security Policy must allow `'wasm-unsafe-eval'`, without which "WebAssembly is blocked from loading and executing" (MDN) |
| iPadOS and other targets without JIT (Tier 2) | The reference interpreter, compiled into the app | Avoids interpreting compiled Wasm on Pulley; phase 2 benchmarks the interpreter, Pulley and wasmi (an interpreter with "built-in support for fuel metering") and records the choice |
| Tier 3 | Wasmtime with Cranelift where supported, otherwise Pulley or the interpreter | Results enter shared caches only after the determinism suite passes (PLT) |

The conformance suite, `ING-O-1`, runs every corpus program on all Tier 1 targets and both executors, and compares values, failures, fuel and Kiln call sequences bit for bit.

### Performance targets and evidence plan

| Measure | Target | Benchmark |
| --- | --- | --- |
| Ingot share of a 200-feature rebuild | At most 2% of the 2 s contract budget (target) | Golden product 1 and the MEC rebuild benchmark, with operations replaced by cached results |
| Plain numeric Ingot versus idiomatic Rust | Within 1.5× natively and 3× in browsers (target) | `ingot-bench` kernels: involute tooth points, tolerance stack of 10⁴ terms, Sobol sampling, a 10⁵-element pattern layout, table lookups |
| Interpreter versus compiled code | Interpreter within 15× of compiled code (target); used only for cold code and stepping | Same kernels |
| Front end | Re-check of an edited 2,000-line module in under 30 ms (target) | Edit-replay corpus |
| Drag specialization | Residual program per frame under 1 ms for golden-product drags, excluding operations (target) | UIX drag scripts |

Phase 0 runs these kernels against a Cranelift JIT prototype and a register VM prototype before the code generator freezes. If compiled Wasm misses the numeric target by more than 25% natively, the fallback in contract section 4 applies to the hot code (see "Rust features"), and the hot pattern becomes an operation candidate through the promotion path.

## Rust features: the fallback path

Contract section 4 allows features written in Rust and compiled to Wasm components, with generated Ingot bindings, if Ingot underdelivers. ECO's rule decides when to use it (D-ECO-6). Ingot supplies the macro, the binding generator and the rules that keep such features first-class: typed signatures with units, dialogs, provenance naming, failures with fixes and the same determinism.

### The author's view

```rust
use crucible_sdk::prelude::*; // Length, Angle, Body, Plane, OpCtx, Site; generated from WIT

/// Involute spur gear tooth profile, closed, centered on the origin.
#[ingot::feature(package = "acme::gears", category = "Power transmission", icon = "gear")]
pub fn involute_profile(
    #[ingot(range = "0.1mm..=50mm")] module: Length,
    #[ingot(range = "6..=400")] teeth: u32,
    #[ingot(default = "20deg", range = "14.5deg..=30deg")] pressure_angle: Angle,
    #[ingot(default = "0mm")] backlash: Length,
    ctx: &mut OpCtx,                                                // supplied by the host; not in WIT
) -> Result<Body, GearError> {
    let rb = module * teeth as f64 * pressure_angle.cos() / 2.0;   // base radius, still a Length
    let mut s = ctx.planar_builder(Plane::XY, ctx.site("profile")); // explicit, stable call site
    for i in 0..teeth {
        let flank = involute_points(rb, module, i, backlash)?;     // detmath::cos, sin inside
        s.add_spline(ctx.site_indexed("flank", i), &flank)?;       // each entity gets a site key
    }
    s.finish_region().map_err(GearError::from)                     // a closed planar region Body
}

#[derive(ingot::Error)]
pub enum GearError {
    #[ingot(code = "GEAR001", fix = "increase teeth to at least {min} or add profile shift")]
    Undercut { teeth: u32, min: u32 },
    #[ingot(code = "GEAR002")]
    Build(BuildError),
}
```

The SDK's quantity types come from the same kind table as Ingot's prelude, so `module * cos(angle)` keeps its dimension in Rust and the macro checks each parameter type against the generated WIT alias. Each operation call and each created entity takes an explicit `Site` key. The host combines it with the component call's own `OpSite`, so entities created inside Rust get names that survive edits, like entities created by Ingot.

### What the macro generates

The macro writes three artifacts and a test. A build fails if any artifact checked into the package differs from the regenerated one.

```wit
// wit/acme-gears.wit (generated)
package acme:gears@1.2.0;

interface involute {
    use crucible:units/si@1.0.0.{length, angle};
    use crucible:geom/types@1.0.0.{body};
    use crucible:geom/build@1.0.0.{build-error};

    variant gear-error {
        undercut(tuple<u32, u32>),
        build(build-error),
    }

    involute-profile: func(module: length, teeth: u32, pressure-angle: angle, backlash: length)
        -> result<body, gear-error>;
}

world gears {
    import crucible:geom/build@1.0.0;
    import crucible:geom/ops@1.0.0;
    import crucible:host/diagnostics@1.0.0;
    export involute;
}
```

```
// src/generated/involute.ingot (generated by ingot-bindgen from acme:gears@1.2.0; do not edit)

#[component(package: "acme:gears@1.2.0", export: "involute/involute-profile", fuel: 5e9)]
extern fn involute_profile_raw(module: Length, teeth: Int, pressure_angle: Angle, backlash: Length)
    -> Result<Body, GearError>

/// Involute spur gear tooth profile, closed, centered on the origin.
#[feature(category: "Power transmission", icon: "gear")]
pub feature involute_profile(
    module: Length in 0.1mm..=50mm,
    teeth: Int in 6..=400,
    pressure_angle: Angle in 14.5deg..=30deg = 20deg,
    backlash: Length = 0mm,
) -> Sketch {
    sketch_from_body(involute_profile_raw(module, teeth, pressure_angle, backlash)?)
}
```

The third artifact is the `wit-bindgen` glue: the macro calls `wit_bindgen::generate!` for the world and implements the generated `Guest` trait, converting SI `f64` values into SDK quantities and `GearError` into the WIT variant. `ingot-bindgen` also emits `GearError` as an Ingot enum that implements `Error`, carrying the codes and fix templates declared in Rust, so `Undercut` reaches the user as `GEAR001` with its fix.

### Rules for Rust features

| Rule | Reason |
| --- | --- |
| The binary is pinned in the lockfile by the SHA-256 of its determinized form (ECO) | Rebuilding with another toolchain cannot change an old design |
| Evaluation world only: no clocks, randomness, files or network | Contract section 7 |
| Randomness only from a `seed` parameter that the wrapper passes from an `Rng` | Explicit randomness |
| Every operation call and created entity takes a `Site` key; keys must be unique per call, or the host fails with `ING8201 DuplicateSite` | Stable `EntityId`s |
| Operation calls go through `crucible:geom/ops`; the host serves them through Kiln with the component call as parent, so nested results are cached and shared | No second path to the engine |
| Fuel is metered by PLT's instrumentation and limited by the wrapper's `fuel:` | Deterministic limits |
| The wrapper is the public interface; the raw `extern fn` is `pub(package)` | Dialogs, docs and semantic-version checks see one typed signature |

**Decision D-ING-15:** The fallback is an attribute macro, `#[ingot::feature]`, that generates the WIT world, the `wit-bindgen` glue and a typed Ingot wrapper from one Rust signature; the wrapper is ordinary Ingot and the only public face of the feature. *Why:* authors write one signature, the units and ranges they declare reach Ingot's type checker and dialogs, and users cannot tell a Rust feature from an Ingot one except by reading its source; the architecture does not change, as contract section 4 requires. *Rejected:* hand-written WIT plus hand-written wrappers (three signatures that drift); native Rust plugins (unsafe, per-platform and impossible in browsers, as ECO's D-ECO-6 already rejects); generating Rust from Ingot (inverts the dependency and puts a Rust toolchain in the loop).

`sketch_from_body` wraps the region Body as a `Sketch` with an empty constraint system, so downstream features treat it like any other profile. A Rust feature gives up two things. The debugger cannot step inside it and shows only its inputs, outputs and nested operations. It has no forward-mode derivative unless the component exports a tangent function, which the macro wires up when `#[ingot::feature(tangent = …)]` names one.

## Modules, packages and versions

### Modules and visibility

A package is a directory with a manifest, `ingot.toml`, and a source tree under `src/`. Each `.ingot` file is a module, and directories nest modules. `src/lib.ingot` is the package root, and `src/main.ingot` is the root of a design repository, whose `pub` items are its outputs: Parts, Assemblies, drawings, checks.

| Visibility | Syntax | Visible to |
| --- | --- | --- |
| Private | none | The module and its child modules |
| Package | `pub(package)` | Every module of the package |
| Public | `pub` | Dependents; part of the semantic-version interface |

A `use` path begins with a dependency's name (`std::mech`), with `package` for the current package's root, or with `self` and `super` for relative paths. `use` brings names into scope: `use std::mech::{sketch, extrude}`, `use acme::gears::involute_profile as gear_profile`, `use std::mech::gdt::asme::*`. Glob imports are allowed but lose to explicit names, and two globs that supply the same name make that name ambiguous at its use (`ING1201`). Module imports form an acyclic graph (`ING1301` on a cycle), as in KCL, which rejects a cycle with `circular import of modules is not allowed`.

The prelude, which every module sees, holds the primitive and core types, the dimension kinds, `Option`, `Result`, the collection types, the common roles and the operators' traits. It changes only with an edition.

### Manifest

ECO proposed `ingot.toml` and `ingot.lock` and left the module system to this tab; Ingot keeps both names. Ingot owns the language keys of the manifest, and ECO owns the registry keys (license, components, capabilities).

```toml
[package]
name = "acme::gears"            # namespace::name; namespaces are registry-owned (ECO)
version = "1.2.0"
edition = "2027"
gdt-dialect = "asme"            # "asme" or "iso"; required if the package attaches GD&T controls

[dependencies]
"std::mech" = "1"               # caret requirement, as in Cargo: >=1.0.0, <2.0.0
"acme::fasteners" = "2.3"

[language]
display = { Length = "mm", Stress = "MPa", Temperature = "degC" }   # display profile default
fuel = { default = 1e9, max = 1e11 }                                  # per feature call; within the organization ceiling
```

### Semantic versioning of the interface

SemVer 2.0 applies to the public interface of the package. At publish, the registry diffs it against the previous version and refuses a minor or patch release that breaks it, as ECO specifies after cargo-semver-checks. Ingot defines what "breaks" means.

| Change | Required release |
| --- | --- |
| Remove or rename a public item, parameter or record field | Major |
| Change a parameter's dimension, kind or type | Major |
| Add a parameter without a default | Major |
| Narrow a parameter's checked range | Major |
| Add a variant to an enum without `#[non_exhaustive]` | Major |
| Remove or rename a declared role or a public coordinate system | Major: every downstream query or mate that uses it breaks |
| Change a default value | Minor, labelled "output-changing" (ECO D-ECO-14) |
| Add a parameter with a default, an item, a role, or a variant to a `#[non_exhaustive]` enum | Minor |
| Widen a parameter's checked range | Minor |
| Change only documentation, metadata or private code | Patch; output changes are measured and labelled by ECO |

### Lockfile

`ingot.lock` is TOML, sorted, and written only by tools. It pins everything a build reads that is not in the repository's own source.

| Section | Content | Owner |
| --- | --- | --- |
| `[language]` | The language behavior version: evaluation semantics, the fuel cost table, the lowering rule for operator chains such as `a + b + c`, and std numeric functions | ING |
| `[[package]]` | Name, exact version, registry, source SHA-256, component and browser bundle SHA-256, signature digest, granted capabilities | ECO, using ING's resolution |
| `[operations]` | One behavior version per operation id, as in `"anvil::blend" = 2` | Kiln and the operation owners |
| `[[asset]]`, `[[external]]` | Assets and External inputs by SHA-256 | ECO |

```toml
# ingot.lock: generated by `crucible update`; do not edit
format = 1

[language]
behavior = 3

[operations]
"anvil::blend" = 2
"anvil::boolean" = 4
"anvil::extrude" = 1
"anvil::resolve" = 1
"flux::solve_linear" = 1

[[package]]
name = "std::mech"
version = "1.4.2"
registry = "crucible"
source = "sha256:…"
signature = "sha256:…"

[[package]]
name = "acme::thermal"
version = "0.4.0"
registry = "acme-internal"
source = "sha256:…"
components = { radiation = "sha256:…", radiation-browser = "sha256:…" }
```

The compiler behavior version that keys front-end nodes (KLN graph model) is distinct from the language behavior version: compiler releases may change diagnostics and speed, but never values, failures or fuel for a pinned language behavior version. A compiler release that changes any of those for an unchanged program is a defect, and the conformance corpus catches it (`ING-O-1`).

**Decision D-ING-16:** The lockfile pins a language behavior version alongside the operation versions, and a toolchain implements every language behavior version newer than the oldest one in its support window, as Anvil and Flux do for operations. *Why:* an old design must rebuild identically (contract section 4), and the language's own semantics, such as fuel costs or std numeric functions, are part of its result just as operation behavior is. *Rejected:* pinning the toolchain release (forces old toolchains to be kept runnable for every design); letting editions carry behavior (ECO's D-ECO-23 forbids editions from changing behavior, and Ingot agrees).

Resolution uses PubGrub, which can "explain errors more clearly than the alternatives". A failure becomes `ING7001` with PubGrub's derivation as notes and relaxations as fixes. Two major versions of one package may coexist in one build, as ECO proposes. Their types are distinct, and passing a value from one to the other fails with `ING7201`, naming both versions and the value's path.

### Editions and migrations

Editions follow Rust's model and ECO's D-ECO-23. Each package declares its edition; packages of different editions link into one build; editions change surface syntax, the prelude and lint defaults, never behavior. Rust's guide requires crates of different editions to interoperate, so its edition changes tend to be "skin deep". Ingot holds editions to the same rule. Every edition lowers to the same IIR.

A migration is a list of syntactic rewrites, each a `Fix` from a lint that the new edition makes an error. `crucible migrate` runs four steps:

1. Apply every machine-applicable fix on the lossless tree, preserving comments and `BlockId`s, so the live document and merge history follow the code.
2. Re-run the formatter on touched blocks only.
3. Compare the IIR of every item before and after. Any difference in IIR, other than spans, rejects the migration for that item and reports it.
4. Build the package's test designs and examples with both editions and require identical output hashes (ECO's O-ECO-13).

Language changes, including new editions, go through the public RFC process that ECO's governance defines, and each accepted change lands with its conformance tests. Step 3 is stronger than Rust's practice, whose guide notes that "Cargo's automatic migrations aren't perfect". It works because Ingot has a single IR with no edition-dependent lowering. A rewrite that cannot preserve the IIR is not offered as automatic; the migration lists it with a placeholder fix for a person or an agent.

## Feature metadata, dialogs and documentation

### Declaring a dialog

A feature's signature generates its dialog, its documentation page and its agent tool description. Attributes refine them, so no separate UI description exists.

| Source element | Generated UI |
| --- | --- |
| Parameter type `Quantity<D>` | Numeric field with unit, accepting expressions after `=` (UIX) |
| `Tol<T>` parameter, or a `T` parameter with a toleranced default | Value field with a tolerance sub-field: symmetric, deviations, limits or fit code |
| `Bool` | Toggle |
| `enum` | Segmented control up to 5 variants, otherwise a dropdown; variant doc comments are tooltips |
| `Query<K>` | Selection field showing the readable query; the filter comes from `K` and the parameter's filters |
| `Material`, catalog part types | Pickers bound to the material library and the parts catalog |
| `Option<T>` | An enable toggle with the field for `T` |
| Record type | A group with the record's fields |
| `[T]` | A list editor |
| `in` range on a parameter | Bounds for the field and the slider, checked at evaluation (`ING6501`) |
| Doc comment of a parameter | Help text |

```
/// Counterbored hole for socket head cap screws.
#[feature(category: "Holes", icon: "cbore", handles: [radial(dia), linear(depth, along: axis)])]
pub feature cbore_hole(
    body: Body,
    /// Where to place the hole axes.
    #[ui(filter: planar)]
    at: Query<Point>,
    /// Screw size from ISO 4762.
    screw: MetricScrew = M6,
    #[ui(group: "Depth", visible_if: |p| p.extent == Blind)]
    depth: Length in 1mm..=500mm = 12mm,
    #[ui(group: "Depth")]
    extent: HoleExtent = Blind,
    /// Diametral clearance class from ISO 273.
    #[ui(advanced)]
    fit: ClearanceFit = Medium,
) -> Body { … }
```

| Attribute | Meaning |
| --- | --- |
| `#[feature(category:, icon:, handles:)]` | Toolbox placement, icon name, manipulator handles (UIX handle kinds) |
| `#[ui(group:, advanced, visible_if:, step:, filter:, label:)]` | Grouping, progressive disclosure, conditional visibility, slider step, selection filter, label override |
| `#[roles(…)]` | The roles the feature creates, for queries and documentation |
| `#[fuel(…)]` | A raised fuel limit, within the manifest maximum |
| `#[example]` | Marks a doc-comment code block as a compiled, evaluated example |
| `#[deprecated(since:, instead:)]`, `#[removed(in:, instead:)]` | Lifecycle with fix-its |

`visible_if` takes a pure closure over the parameter record. The front end evaluates it on default values to check that it type-checks and cannot fail, and the UI evaluates it in the reference interpreter as values change. FeatureScript expresses the same thing with `if` statements in its `precondition` block, where each parameter may appear only once; a closure on the parameter keeps one declaration per parameter and allows any condition over the record.

**Decision D-ING-17:** Dialogs are generated from feature signatures, types, doc comments and a small attribute vocabulary, with conditional visibility as pure closures; there is no separate dialog language. *Why:* one declaration serves the dialog, the docs, semantic-version checks and agent tool schemas, so they cannot drift; Onshape's precondition annotations show that dialogs generated from feature declarations work at scale, and typed parameters remove most of their annotations. *Rejected:* FeatureScript-style precondition blocks (a second statement language whose only purpose is UI); hand-built dialog descriptions (drift from the signature).

### Documentation

`crucible doc` generates reference pages from signatures, doc comments, roles, units, ranges and examples. Every `///` code block is compiled and, when marked `#[example]` or fenced as `ingot,eval`, evaluated in CI with its checks. A public item without a doc comment fails the registry's coverage gate (ECO). The same data feeds AGT's documentation resources and tool schemas (D-AGT-23).

## Calling Wasm components

### Binding conventions

`ingot-bindgen` reads a component's WIT and writes Ingot `extern` declarations plus a typed wrapper. ECO keeps units out of WIT types and passes SI `f64` values with `crucible:units` aliases; the generator maps each alias to a dimension.

| WIT | Ingot |
| --- | --- |
| `bool`, `s8` to `s64`, `u8` to `u32` | `Bool`, `Int` |
| `u64` | `Int`, failing with `ING6101` above 2⁶³ − 1 |
| A `u64` parameter or field named `seed` | `Seed`, following ECO's convention that it is "the only source of randomness" |
| A parameter or field of ECO's `fidelity` enum | Omitted from the Ingot signature; the host fills it from the evaluation request, because Ingot code cannot observe fidelity |
| `f32`, `f64` | `Real` |
| `crucible:units/si` aliases (`length`, `force`, `stress`, `temperature`, …) | `Length`, `Force`, `Stress`, `Temperature` (kelvin; affine conversion in the wrapper) |
| `string` | `String`; component-authored strings become `ExternalText` values (AGT) |
| `list<T>`, `option<T>`, `result<T, E>`, `tuple<…>` | `[T]`, `Option<T>`, `Result<T, E>`, tuples |
| `record`, `variant`, `enum`, `flags` | `record`, `enum`, `enum`, `Set<Enum>` |
| `crucible:geom` `body`, `crucible:field` `field` resources | `Body`, `Field<…>` handles |
| Other resources | Opaque handle types, owned by the wrapper |
| kebab-case names | snake_case functions and fields, PascalCase types |

A WIT parameter typed as a bare `f64` gets the generic `Real` type, and the generator emits `ING8101` asking the author to supply a unit alias or an override in `ingot-bindgen.toml`. A wrapper that a person refines keeps the generated signature as a compatibility check, so a WIT change that alters it fails the build.

### The determinism contract for component calls

| Rule | Mechanism |
| --- | --- |
| A component export call is an Op, keyed by the component's determinized SHA-256, the export, the arguments' `ObjectId`s and canonical encodings, and the instrumentation version | Kiln `OpKey` with `impl` (KLN) |
| Evaluation-world components import only `crucible:` interfaces, never WASI clocks, random, files or sockets | ECO contexts; PLT install check |
| Randomness reaches a component only as a `seed: u64` argument, derived by the wrapper from an `Rng` | ECO's `request.seed` convention |
| The manifest's component entry sets the maximum fuel; the wrapper's `fuel:` sets the per-call limit within it; PLT's instrumentation enforces it on every engine | ECO manifest; D-PLT-22 |
| Traps, fuel exhaustion and stack exhaustion are deterministic failures, cached; host resource failures are environmental, never cached | PLT failure table; D-KLN-6 |
| Results with error estimates map to `Approx<T>`; a component's `outside-envelope` maps to the `OutsideValidity` flag | Wrapper convention |
| Diagnostics written through `crucible:host/diagnostics` attach to the call's source span, ordered by emission | Write-only accumulator |

Wasm components are CPU-only (ECO). A component never calls back into Ingot code; it calls operations through `crucible:geom/ops`, which the host serves through Kiln.

## Tooling

### Lossless syntax tree

`ingot-syntax` parses into a lossless green-red tree in the design rust-analyzer uses, a "lossless, or full fidelity" tree that keeps every character, including whitespace and comments. Green nodes are immutable and interned; red nodes add parent links and offsets. Crucible uses the `rowan` crate (MIT or Apache-2.0). The parser never stops at an error: it wraps malformed input in `ERROR` nodes and leaves missing pieces absent, so every editor state has a tree, a type-checked AST and, with holes, an evaluation.

Every byte belongs to exactly one block, as Kiln's live document requires. Ingot declares these grammar nodes as blocks:

| Block kind | Head | Children | Tail |
| --- | --- | --- | --- |
| File | Leading inner attributes and module docs | Items | Trailing trivia |
| Item (`use`, `fn`, `feature`, `extern`, `record`, `enum`, `trait`, `impl`, `type`, `kind`, top-level `let`) | Attributes, docs, signature up to the opening brace | Parameters, fields, variants, statements | The closing brace |
| Parameter, field or variant | Its text up to the comma | none | none |
| Statement | The statement's text up to its first nested block, if any | Arms: its builder block, the branches of `if` and `match`, the body of `for` | Text after the last arm |
| Arm | Its header text (`{`, `else {`, `Some(x) =>`) | The arm's statements | Its closing brace or comma |
| Table row | The row | none | none |

Comments and blank lines belong to the head of the block that follows them, and trailing comments on a line belong to the block on that line. Moving a block therefore moves its comments, and a concurrent edit inside a block follows the block, as Kiln's tree CRDT intends. Lists that Kiln merges as sets are declared as order-insensitive in the grammar: `use` lists, named arguments, record literal fields and attribute arguments.

### Canonical formatter

`crucible fmt` produces one canonical layout, and the same code formats every edit an agent or the GUI makes (AGT D-AGT-4). The formatter is idempotent and preserves comments, `BlockId`s and the token sequence.

| Rule | Choice |
| --- | --- |
| Width | 100 columns |
| Indentation | 4 spaces |
| Breaking | A call that does not fit breaks after `(`, one argument per line, trailing comma |
| Pipelines | One stage per line when the chain does not fit, each line starting with `\|>` |
| Alignment | Only table columns, and `=` in consecutive `let` statements of one block if they already align; never anything that turns a one-line edit into a multi-line diff |
| Units | Canonical ASCII spellings; `+-` becomes `±` |
| Literals | Kept as written, except unit spelling |

The formatter works per block, so formatting a touched block never moves another block's bytes. A file formatted with a different edition's formatter differs only in that edition's rules.

### Structural editing

Every GUI action becomes a `SourcePatch` list computed on the tree, then applied as Kiln's reconcile step requires: edits inside one block are text operations on that block, and structural changes are tree operations. AGT's structured edits lower to the same functions.

| GUI or agent action | Minimal source edit |
| --- | --- |
| Change a parameter value in a dialog | Replace one literal token; keep its unit unless the user typed another |
| Drag a dimension or face | Replace the literal the edit plan chose (UIX D-UIX-15); `SolveLiteral` rewrites only that literal |
| Add a feature after another | Insert one statement block after the anchor statement, naming the binding with a fresh name derived from the feature (`fillet_2`) |
| Delete a feature | Remove the statement block and its attached comments, after the dependency check; uses of its binding become fix-it diagnostics |
| Reorder features | Move a statement block; refused with the reason if it would use a binding before its definition |
| Suppress | Add or remove the `#[suppressed]` attribute token |
| Rename | Rename the symbol in every module of the package, as an atomic patch set |
| Set a tolerance | Rewrite `4mm` to `4mm ± 0.1mm`, or change one deviation token |
| Add a check | Insert a `require` statement at the end of the feature body, or attach `.require(…)` to the returned expression when the body is a single expression |
| Change a sketch seed | Replace the seed literal tokens of one entity call |

Each action produces the smallest patch that the formatter leaves unchanged. Oracle `ING-O-10` replays recorded GUI sessions and checks that every patch touches only the blocks the action names, keeps every comment and keeps every `BlockId` outside them.

**Decision D-ING-18:** The grammar is designed for structural editing: newline-terminated statements, one statement per block, comments owned by the following block, named arguments that merge as sets, and atomic literals. *Why:* Kiln's live document needs a block for every unit of concurrent work and an owner for every byte, and the UI needs one-token edits for every dialog change; these constraints are cheap when designed in and impossible to add later. *Rejected:* a projectional editor with no text (code review, diff tools and agents all work on text); free-form layout with semicolons (two layouts for one program would mean two diffs for one edit).

### Language service

The language service implements LSP 3.17 semantics in `ingot-service`, and the UI and agents reach it through `api` (UIX code panel). It also speaks LSP directly for external editors such as VS Code, Zed and Neovim.

| Feature | Ingot specifics | Phase |
| --- | --- | --- |
| Diagnostics (pull model) | Compile diagnostics plus evaluation failures from Kiln, attached to spans | 1 |
| Semantic tokens | Units, quantity literals, roles and query filters get their own token types | 1 |
| Hover | Type with dimension in display units, evaluated value with its bound, tolerance limits, doc comment | 1 |
| Inlay hints | Evaluated values (`width / 2  ⟨30 mm⟩`), inferred dimensions, the `Tol`-to-nominal coercion, `Option` coercion | 1 |
| Completion | Context-aware: units after numbers, roles valid for a query's anchor, parameters of the call, enum variants for the expected type | 1 |
| Go to definition, references, rename | Across the package and its dependencies' public items | 1 |
| Code actions | Every diagnostic fix; refactors: extract feature, inline binding, convert literal to parameter, add tolerance | 1 |
| Call and type hierarchy | Feature call graph; trait implementations | 2 |
| Inline values | Values of bindings at the debugger's current frame | 2 |
| Notebook documents | REPL notebooks (below) | 2 |
| Source map | `EntityId` to creating `OpSite` to span, and back (UIX cross-probing) | 1 |

Target: completion and hover within 50 ms, and diagnostics for an edited 2,000-line module within 100 ms, on the reference laptop (target).

### Debugger

The debugger runs a feature call in the reference interpreter, reading every operation result from the cache, so stepping never re-runs geometry and never changes a result. It is exposed through the Debug Adapter Protocol for external editors and through `api` for the UI.

| Capability | Behavior |
| --- | --- |
| Breakpoints | On statements, on feature entry, conditional on any pure expression |
| Stepping | Into, over and out, across feature calls; Rust features and Wasm components appear as opaque frames with their inputs, outputs and nested operations |
| Variables | Every binding with type and value; Bodies, Parts and Fields as handles the viewport can display |
| Intermediate Bodies | The viewport shows the Body bound at the current frame, with entities colored by creating `OpSite`, and the bodies of the last three statements as ghosts |
| Queries | Evaluate any query against the current frame's Body and see the resolved entities highlighted, or the `ResolveError` |
| Reverse stepping | `stepBack` and `reverseContinue`, which DAP defines behind `supportsStepBack`. Evaluation is pure and recorded, so stepping back re-enters a recorded state |
| Failure stop | On any failure, stop at the expression the replay identified, with the fix list |
| Fuel and time | Fuel consumed per statement; cached and recomputed operations marked with their recorded cost |

### REPL and notebooks

`crucible repl` and the UI's notebook mode evaluate cells against a design. A cell may define items, evaluate expressions or attach checks. Each cell compiles as a module that imports the previous cells' public names, so notebooks keep Ingot's static typing.

Cells evaluate through Kiln, so re-running a notebook recomputes only what changed. A notebook is saved as an `.ingot` file whose cells are separated by `//% cell` comment markers, which keeps it diffable, mergeable and editable as plain text. Outputs are not saved in the file. They are Kiln values, regenerated or fetched from the cache on open. Notebooks are where agents explore before writing a Proposal, and where analysts write studies that later move into a package.

### Test framework

Tests are Ingot functions marked `#[test]`, in `tests/` or beside the code. Expensive assertions run as Kiln nodes, cached like everything else.

```
#[test]
fn bracket_mass_and_fit() {
    let p = bracket(width: 80mm, thickness: 5mm ± 0.1mm)
    assert_close(p.body.volume(), 24.1cm3, rel: 1%)          // illustrative value: plate, web and two fillets
    assert_valid(p.body)                                  // anvil::check_body: closed, manifold, no self-intersection
    assert_resolves(p.body.faces(role: side(any)), count: 4..)
    assert_no_notes(p.body)                               // no merge notes on any query in the build
    assert_checks_pass(p, fidelity: SignOff)              // every attached check, evaluated at sign-off
}

#[test(golden)]                                           // compares with a stored reference by ObjectId
fn bracket_geometry_unchanged() { bracket() }

#[test(property, cases: 256)]                             // inputs drawn from the parameter ranges
fn bracket_builds_everywhere(p: Params<bracket>) {
    assert_valid(bracket(..p).body)
}
```

| Assertion | Contract |
| --- | --- |
| `assert_close(a, b, rel:, abs:)` | Passes only if the enclosures of `a` and `b` lie within the tolerance; fails with the margin; an `Unknown` bound fails |
| `assert_valid(body)` | Anvil's body checker; fails with the violations |
| `assert_same_shape(a, b, within:)` | Certified Hausdorff distance below `within` |
| `assert_resolves(q, count:)` | The query resolves with the given cardinality |
| `assert_fails(expr, code:)` | `expr` fails with a failure of that code |
| `assert_checks_pass(x, fidelity:)` | Every check attached to `x` passes at that fidelity; `Undecided` fails the test with the accuracy needed |
| `assert_volume`, `assert_mass_properties`, `assert_interference_free(asm)` | Measurements and assembly checks with bounds |
| Golden tests | Store the result's `ObjectId` in a reviewed file; a change shows the geometric diff |
| Property tests | Inputs drawn by a seeded `Rng` from parameter ranges; a failure is shrunk to a minimal parameter record and printed as a reproducible call |

Tests are deterministic, so a flaky test is a defect in the engine, never in the test. Tests under `oracles/` are protected (contract section 7).

### Benchmarks

`#[bench]` functions measure Ingot execution separately from operations. The runner reports fuel, which is deterministic, together with wall time, which is not. CI tracks fuel exactly, flagging any change, and tracks time statistically on fixed hardware. A benchmark can request `ops: cached` to measure Ingot overhead alone or `ops: cold` to measure a full rebuild.

## Comparison with existing languages

| Aspect | Zoo KCL | Onshape FeatureScript | CadQuery | build123d | OpenSCAD | Ingot |
| --- | --- | --- | --- | --- | --- | --- |
| Host | Own language; Rust implementation, MIT | Own language inside Onshape | Python library on OpenCascade through OCP | Python library on OpenCascade | Own language; CGAL listed as a build prerequisite | Own language; Rust implementation |
| Typing | Numeric types with units (`number(mm)`); bare numbers take the file default | Dynamic, with `ValueWithUnits` tracking dimensionality | Dynamic Python | Dynamic Python with type hints | Dynamic; numbers, booleans, strings, vectors, `undef` | Static, inferred in bodies, required signatures |
| Units | Lengths, angles and counts; "KCL doesn't support area, volume, or other higher-dimension units" | Dimensional analysis; mixing incompatible units throws | None in the language | None in the language | None | Full dimension algebra with rational exponents, kinds and affine temperatures, all at compile time |
| Tolerances | None | None in the language | None | None | None | `Tol<T>` with worst-case affine arithmetic, explicit statistics, GD&T as typed values |
| Entity selection | Tags on sketch segments [unverified: tag syntax] and sketch-on-face references | Queries such as `qCreatedBy(id + …)` over hierarchical feature ids | String selectors such as `">Z"` | Selectors, `sort_by`, `group_by`, `filter_by`; `Select.LAST` and `Select.NEW` from operation history | No entity references [unverified: from general knowledge] | Provenance queries with roles, history selectors and certified filters; no positional access |
| Composition | Pipelines with `\|>` and an unlabeled first parameter | Features take `context`, `id` and a definition map | Fluent method chains on `Workplane` | Builder contexts or algebra mode | CSG modules | Pipelines, methods from `impl`, builder blocks |
| Purity | Mostly functional | Deterministic: no external input, time or randomness; value semantics with explicit `box` | Python: anything | Python: anything | Functional; last assignment wins | Pure, with fuel and explicit keyed randomness |
| UI generation | Point-and-click cannot edit sketches inside custom function bodies | Precondition annotations generate dialogs | None | None | Customizer comments [unverified] | Signatures and attributes generate dialogs, handles and docs |
| Versioning | `kclVersion` per program, mixing versions an error from 3.0 | Standard library imported with a pinned version string | Python packaging | Python packaging | Releases | Editions per package, lockfile pins of language and operation behavior |
| Execution | Commands sent to Zoo's hosted engine, whose view streams back as video | In Onshape's cloud service [unverified: not on the pages opened] | Local Python | Local Python | Local | Compiled to Wasm; runs locally on every Tier 1 target and in the browser |

### What Ingot adopts

| From | Adopted | Where |
| --- | --- | --- |
| KCL | The pipeline operator feeding the first parameter, keyword arguments, units as literal suffixes, per-file modules with explicit exports, versioned language settings | Lexical syntax; modules; editions |
| FeatureScript | Features as functions whose parameters generate dialogs; a std library written in the user language and published as source; determinism forbidding time and randomness; value semantics; queries over creation history | Metadata; principles; queries |
| CadQuery | Fluent chaining for readable scripts, through methods and pipelines | `.` and `\|>` |
| build123d | History selectors (`new`, last operation), topological filters by adjacency, explicit locations for patterns | Query language |
| OpenSCAD | Declarative, side-effect-free modeling as text that diffs and versions well | Purity and formatting |

### What Ingot rejects

| From | Rejected | Why |
| --- | --- | --- |
| KCL | File-level default units, bare numbers of unknown unit, no area or volume units, arithmetic that does not track units (KCL's documentation gives `10in * 25.4` as `254in`) | Principle 5: the compiler checks physics |
| FeatureScript | Threading `context` and `id` through every call; untyped definition maps; precondition statements as a UI language; run-time unit errors | Typed signatures and dataflow make them unnecessary |
| CadQuery | String selectors; Python's open world (files, network, randomness, clocks) during evaluation; implicit workplane state | Determinism, typed queries, explicit values |
| build123d | Builder modes that mutate a running total through context managers; positional slicing after sorting as the main selection method | Purity; positional selection breaks when dimensions change |
| OpenSCAD | Dynamic typing; `undef`; no entity references; special variables that set tessellation globally [unverified: not on the page opened] | Typed failures, provenance queries, explicit `ErrorBound`s |

**Decision D-ING-19:** Crucible builds Ingot's implementation from scratch and does not fork KCL's MIT-licensed implementation; it studies KCL's test programs and documentation as references, with attribution. *Why:* the parts of a language implementation that matter most here are new: compile-time dimension algebra with rational exponents, affine quantities, `Tol` and `Truth` types, provenance queries, staging of symbolic values, compilation to deterministic Wasm, fuel and the block grammar for the CRDT. `kcl-lib` couples execution to an engine connection (cloning its `ExecutorContext` shares the same connection, per its API documentation), while Ingot runs inside Kiln and keeps every operation call out of the language runtime. The reusable pieces, a lexer and parser, are about a month of work against Ingot's own grammar. *Rejected:* forking `kcl-lib` (we would replace most of it while inheriting its semantics, such as default units, and lose a clean provenance story for oracles); seeking compatibility with KCL source (its unit semantics conflict with principle 5). An importer that translates KCL programs into Ingot, mapping default units explicitly, is phase 3 work in the `io/` crates.

## Worked examples

### 1. A machined part

Golden product 1 is a machined bracket. This version has counterbored holes, a pocket and a datum scheme.

```
//! Machined mounting bracket (golden product 1).
use std::mech::{sketch, rect, extrude, hole, fillet, chamfer, part, HoleSpec, HoleExtent}
use std::mech::gdt::asme::{datum, position, flatness, profile, mmc, dia}
use std::materials::alu_6061_t6

/// Base plate with four M6 counterbored holes and a lightening pocket.
#[feature(category: "Golden products", icon: "bracket")]
pub feature mounting_bracket(
    length: Length in 60mm..=300mm = 120mm,
    width: Length in 40mm..=200mm = 80mm,
    thickness: Length = 10mm ± 0.05mm,
    hole_inset: Length in 6mm..=30mm = 12mm,
) -> Part {
    let blank = sketch(plane.xy) { rect(center: origin, length, width) } |> extrude(thickness)
    let top = blank.face(role: end_cap)
    let pocket = sketch(top) { rect(center: origin, length - 4 * hole_inset, width - 2 * hole_inset) }
        |> extrude(thickness / 2, dir: -normal)                // Blind, by the implicit variant
    let holes = (blank - pocket)
        |> hole(at: top.corners(inset: hole_inset),
                spec: HoleSpec::counterbore(6.6mm, cb_d: 11mm, cb_depth: 6.4mm),   // M6 cap screw, medium fit
                extent: HoleExtent::ThroughAll)
    let finished = holes
        |> fillet(holes.edges(created_by: pocket, parallel_to: z_axis), 4mm)
        |> chamfer(holes.edges(created_by: blank, adjacent_to: top), 0.5mm)

    let a = datum("A", finished.face(created_by: blank, role: start_cap))
    let b = datum("B", finished.face(created_by: blank, role: side(any), normal: -y))
    let c = datum("C", finished.face(created_by: blank, role: side(any), normal: -x))
    part(finished, name: "Mounting bracket", item: ItemNumber("GP1-100"))
        .material(alu_6061_t6)
        .tolerance(a.aspect, flatness(0.02mm))
        .tolerance(finished.aspects(created_by: holes), position(dia(0.1mm), mmc, datums: [a, b, c]))
        .tolerance(finished.faces(all), profile(0.2mm, datums: [a, b, c]))
        .require(finished.volume() < 0.8 * blank.volume(), name: "lightened")
}
```

`thickness` reaches `extrude` with its tolerance, so the plate thickness carries its zone as PMI and `tolerances(part)` lists it for stack-ups; `thickness / 2` uses only the nominal. `top.corners(inset:)` yields four points, so one `hole` call creates four holes that differ only by index in their `OpSite`. Following MEC's D-MEC-6, `extrude` returns the pocket as a tool body and the difference is written with `-`. The `lightened` check compares two `Approx<Volume>` values, so its outcome is a `Truth`; at the defaults the part keeps about 76% of the blank's volume.

### 2. A parameter flowing through an assembly

A shaft diameter drives a bearing choice from the catalog, the housing bore and a fit check. Changing `shaft_d` re-resolves the bearing, rebuilds the shaft and the housing, and re-evaluates the checks that read them, and nothing else.

```
use std::mech::asm::{assembly, instance, revolute, fastened}
use std::mech::fits::{fit, H7, k6}
use parts::bearings::deep_groove_ball as bearing_62xx       // catalog package (illustrative)

pub record DriveParams {
    shaft_d: Length = 12mm,
    load: Force = 400N,
    speed: AngularVelocity = 3000rpm,
}

pub feature drive_unit(p: DriveParams = DriveParams {}) -> Assembly {
    let brg = bearing_62xx(bore: p.shaft_d)?               // catalog query; the chosen part is pinned in the lockfile
    let seat = fit(p.shaft_d, k6)                            // one site, used twice below
    let shaft_part = stepped_shaft(d: seat, length: 80mm)
    let housing_part = bearing_housing(bore: fit(brg.outer_d, H7), width: brg.width)
    let h = instance(housing_part, fixed: true)
    let s = instance(shaft_part)
    let b = instance(brg.part)
    assembly([h, s, b], mates: [
        fastened(b.csys("outer"), h.csys("bore")),
        fastened(b.csys("inner"), s.csys("seat")),
        revolute(s.csys("axis"), h.csys("axis")),
    ])
    .require(brg.basic_dynamic_rating > 10 * p.load, name: "bearing_capacity")
    .require(brg.limiting_speed > 1.2 * p.speed, name: "bearing_speed")
    .require((seat - brg.bore_tol).limits().hi <= 0.025mm, name: "max_interference")
}

pub let small = drive_unit()
pub let large = drive_unit(DriveParams { shaft_d: 20mm, load: 900N })
```

The last check is a worst-case stack of two sites, the shaft's `k6` fit and the bearing's bore tolerance from its catalog record, so `.limits()` is exact. `bearing_62xx(bore:)` returns `Result`, and `?` turns `ResolveError::NoCatalogMatch` into a failure at that call with the catalog's nearest candidates as fixes. Kiln caches `small` and `large` as separate feature nodes; they share std code and catalog records but no geometry. Editing `speed` re-evaluates only the `bearing_speed` check, because no geometry reads it.

### 3. A check with physics and honest outcomes

```
use std::flux::quick::static_solve
use std::physics::solid::elasticity

pub feature bracket_check(b: Part, load: Force = 1.2kN) -> Part {
    let study = static_solve(elasticity(b), fixed: b.faces(role: wall), loads: [b.face(role: end_cap) => load])
    let peak = study.von_mises.max()                                   // Approx<Stress>, with flags
    let sy = b.material.yield_strength(at: 20degC)
    b.require(peak < 0.6 * sy, name: "static_margin", severity: Error, fidelity: SignOff,
              evidence: Guaranteed, because: "allowable 0.6 Sy for this bracket class")
     .require(study.max_displacement() < 0.1mm, severity: Warning)
}
```

| Situation | Outcome of `static_margin` |
| --- | --- |
| Interactive solve, peak 112 MPa ± 20 MPa; limit 0.6 × 276 MPa = 165.6 MPa (illustrative yield value) | `Undecided(WithinBound)`: FLX's interactive margin rule needs a margin of three times the estimate, 60 MPa, and the margin is 53.6 MPa |
| Sign-off solve, peak 118 MPa ± 1.5 MPa (Guaranteed) | `Pass`; AGT's margin (limit − value) / limit is 28.7% at the estimate, and 27.8% at the bound's upper end, which the report also shows |
| Peak at a re-entrant corner flagged `Singular` | `Undecided(Flagged(Singular))` with fixes: add a fillet, check at a distance, or use a stress-intensity criterion |
| Solve failed to converge | `Error(failure)`, with the solver's diagnostics |

### 4. A toleranced feature with a stack-up

```
use std::mech::fits::{fit, H7, g6}
use std::mech::asm::{assembly, instance, cylindrical}

/// Pin-in-bore joint with a clearance requirement.
pub feature pin_joint(bore_d: Length = 10mm, gap_min: Length = 4um) -> Assembly {
    let bore = fit(bore_d, H7)                              // Tol<Length>: 10.000 to 10.015 mm [unverified: ISO 286-2 table values]
    let pin = fit(bore_d, g6)                               // 9.986 to 9.995 mm [unverified: ISO 286-2 table values]
    let h = instance(block_with_bore(d: bore), fixed: true)
    let s = instance(pin_part(d: pin))
    let clearance = bore - pin                              // affine form in two symbols
    let asm = assembly([h, s], mates: [cylindrical(s.csys("axis"), h.csys("bore"))])
    asm.require(clearance.limits().lo >= gap_min, name: "min_clearance")         // worst case: 5 um, passes
       .require(clearance.rss(k: 3).hi <= 26um, name: "max_clearance_stat")     // statistical: 25.75 um, passes
}
```

`clearance.limits()` gives 0.005 mm to 0.029 mm exactly, because the stack is linear. The statistical check uses each site's declared distribution, here the default normal with limits at ±3σ. σ is 2.5 µm for the bore and 1.5 µm for the pin, so the upper 3σ limit is 17 µm + 3 × 2.92 µm = 25.75 µm. Its report lists that assumption. The `fit` values are sites, so the parts receive them by forwarding and their bore and pin faces carry the fit codes as PMI. If a designer later scales a contributor by an exact factor, the stack stays linear and exact; if they write `sqrt(bore * pin)`, the result gains a remainder symbol, and `clearance.contributors()` reports its share.

### 5. A package with a feature that calls a Wasm component

```
acme-thermal/
├── ingot.toml
├── src/
│   ├── lib.ingot
│   └── generated/solver.ingot           # from ingot-bindgen
├── components/radiation/                # Rust crate, compiled to a Wasm component
│   └── src/lib.rs
├── wit/acme-thermal.wit
└── tests/enclosure.ingot
```

```toml
[package]
name = "acme::thermal"
version = "0.4.0"
edition = "2027"

[dependencies]
"std::mech" = "1"
"std::flux" = "1"

[components.radiation]
path = "components/radiation.wasm"
world = "crucible:physics/solver@1"
context = "evaluation"
fuel = 2e11
```

```
//! Gray-body radiation exchange inside a closed, diffuse enclosure.
use package::generated::solver::{solve_raw, SolveRequest}     // generated from crucible:physics/solver@1

/// Net radiative heat flux on each inner face of the enclosure.
#[feature(category: "Thermal", icon: "radiation")]
pub feature radiation_exchange(
    enclosure: Body,
    hot: Query<Face>,
    cold: Query<Face>,
    emissivity: Real in 0.01..=1.0 = 0.85,
    t_hot: Temperature = 80degC,
    t_cold: Temperature = 20degC,
    accuracy: Real in 1e-6..=0.1 = 0.005,
    seed: Seed = Seed::from(enclosure.faces(all)),
) -> Field<Body, HeatFlux> {
    let temps = Field::per_entity(enclosure, [hot => t_hot, cold => t_cold])   // crosses as kelvin
    let out = solve_raw([enclosure], [temps], SolveRequest {    // fidelity is filled by the host
        parameters: [("emissivity", emissivity)],      // names and dimensions declared here, SI values (ECO)
        tolerance: accuracy,
        seed: Rng::new(seed).split("radiation").seed(),// the component's only randomness
    })?
    let flux: Field<Body, HeatFlux> = out.field("net_flux")?   // checks the recorded dimension (ING8102)
    let recip = out.scalar("reciprocity_error")?
    flux.require(recip < 1e-3, name: "reciprocity", severity: Warning)
}
```

The component crate, abridged:

```rust
wit_bindgen::generate!({ world: "solver", path: "wit" });   // crucible:physics/solver@1

struct Radiation;

impl exports::crucible::physics::solve::Guest for Radiation {
    fn envelope() -> Vec<(String, f64, f64)> {
        vec![("emissivity".into(), 0.01, 1.0)]                   // gray, diffuse walls; non-participating medium
    }

    fn solve(domain: Vec<BodyBorrow>, inputs: Vec<FieldBorrow>, req: Request)
        -> Result<Vec<Output>, SolveError> {
        let faces = facets(&domain[0], req.tolerance)?;           // through crucible:geom/measure
        let f = view_factors(&faces, req.tolerance, req.seed);    // ray sampling on a Philox stream keyed by the seed
        let q = radiosity(&f, emissivity(&req)?, &face_temperatures(&inputs[0])?);
        Ok(vec![per_face_output("net_flux", q, f.error()), scalar_output("reciprocity_error", f.reciprocity_error())])
    }
}

export!(Radiation);
```

The generated wrapper converts SI values, wraps component strings as `ExternalText`, maps `outside-envelope` to the `OutsideValidity` flag and maps `solve-error` variants to failures with fixes. The returned `error-estimate` becomes the statistical entry of the Field's `ErrorBudget`, `Guaranteed` only if the component sets `guaranteed`. The package's test builds two concentric spheres, whose exchange has the closed form Q = A₁σ(T₁⁴ − T₂⁴) / (1/ε₁ + (A₁/A₂)(1/ε₂ − 1)), and asserts the computed flux within the requested accuracy. Because the seed is derived from the enclosure's `EntityId`s, the same design gives the same flux on every platform, and a different design never reuses a cached result by accident.

## Capability catalog

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Lexer and parser | Lossless tree for any input; NFC and unit spelling normalized by the formatter | `ERROR` nodes; diagnostics `ING0xxx`; never a crash | ING-O-2 (round trip), ING-O-3 (fuzzing) | 0 |
| Dimension and kind checking | Rational exponents, eight base dimensions, kinds, affine points | `ING3xxx` with fixes | ING-O-4 | 0 |
| Type inference, records, enums, traits, generics | Bidirectional; required signatures; exhaustive `match`; orphan rule | `ING2xxx` | ING-O-5 | 0 (core), 1 (traits, `dyn`) |
| `Tol<T>` with affine arithmetic | Exact linear stacks; guaranteed enclosures; explicit statistics | `ING4xxx` | ING-O-7 | 1 |
| `Approx<T>` and `Truth` | Outward-rounded bounds; Kleene logic; guaranteed approximations accepted as feature inputs with their bound recorded | `ING6401` in control flow; `ING6403` for estimates as inputs | ING-O-8 | 1 |
| `Decimal` and `Money<C>` support | Exact decimal arithmetic at 10⁻⁹ | Overflow `ING6101`; inexact literal `ING2003` | ING-O-5 | 1 |
| GD&T attachment and dialects | Typed aspects; dialect modules; tombstones | `ING42xx`, `ING43xx`, MEC `InvalidControl` | MEC-O-TL-1 plus ING-O-5 | 1 |
| Queries | Plans resolved by `anvil::resolve`; no positional access | `ResolveError` with fixes; `ING5xxx` | Anvil query oracles plus ING-O-11 | 1 |
| Builder blocks, sketches, symbolic values | `Builder<I, Ctx>`; `Expr<T>`; hash-consed DAGs | `ING1104`, `ING2301`, `ING2402` | ING-O-5, MEC sketch oracles | 1 |
| Families and tables | Record spread, table literals, CSV with unit headers | `ING2105`, `ING3501` | MEC-O-PF-12 | 1 |
| Determinism and explicit randomness | Bit-identical values, failures and fuel on every Tier 1 target | Environmental failures never cached | ING-O-1, ING-O-6 | 0 |
| Fuel and limits | Per feature call, language cost table | `ING63xx` | ING-O-1 | 0 |
| IIR and the Kiln contract | Code hashes; asynchronous calls; program-order failures; overrides | `DependencyFailed` | ING-O-13 (minimal re-evaluation) | 0 |
| Wasm code generator | Deterministic subset, fuel, source maps, Perceus | Validator rejection is a compiler defect | ING-O-1, ING-O-14 (differential fuzzing) | 1 |
| Reference interpreter | Same values, failures and fuel as compiled code | — | ING-O-1 | 0 |
| Drag specialization | Residual program on the forward slice | Falls back to full evaluation | ING-O-12 | 1 |
| Holes and partial evaluation | Evaluation around holes | `ING6001` | ING-O-15 | 1 |
| Derivatives | Dependence; forward mode; reverse through Kiln | `NotDifferentiable { op }` | Taylor tests (FLX) plus ING-O-16 | 1 (dependence, forward), 2 (reverse) |
| Rust features | Macro generates WIT, glue and wrapper | `ING8xxx`; component failures typed | ING-O-17 | 1 |
| Modules, packages, lockfile, PubGrub | Language behavior version pinned | `ING7xxx` | ING-O-18 | 1 |
| Editions and migrations | IIR-preserving rewrites | Non-preserving rewrites reported, not applied | ING-O-19, O-ECO-13 | 2 (first edition change) |
| Metadata, dialogs, docs | Generated from signatures | Coverage gate at publish | ING-O-20 | 1 |
| Formatter and structural edits | Canonical; minimal; comment-preserving | Refused edits explain why | ING-O-10 | 1 |
| Language service | LSP 3.17 semantics | Degrades to plain text editing (UIX) | ING-O-21 (latency) | 1 |
| Debugger | DAP; replay from cache; reverse stepping | — | ING-O-22 | 2 |
| REPL and notebooks | Cells as modules; outputs from Kiln | — | ING-O-5 | 2 |
| Tests and benchmarks | Geometric assertions; golden and property tests | Deterministic failures | Self-hosting: std's own test suite | 1 |
| KCL importer | KCL programs to Ingot with explicit units | Unmapped constructs listed | Round trip on KCL sample programs | 3 |

## State of the art

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Units and dimensions | Units-of-measure types with inference (F#); quantity kinds and affine points (mp-units, after ISO 80000) | F# units of measure (integer exponents); mp-units; Pint for run-time checks | Static rational dimension algebra, kinds, angle as a base dimension, affine temperatures, all erased at run time | ING-O-4: zero unit errors reach evaluation on the seeded-error corpus; check time under 5% of front-end time (target) |
| Tolerance arithmetic | Affine arithmetic (Comba and Stolfi 1993; de Figueiredo and Stolfi 2004); GUM and Supplement 1 for statistics | Spreadsheet worst-case and RSS stacks; commercial 1D stack tools [unverified] | Affine forms per site; explicit RSS and Monte Carlo | ING-O-7: exact limits on linear stacks; enclosure always contains sampled values |
| Approximate comparisons | Interval and three-valued logic for certified predicates | FLX's three-valued checks (D-FLX-15) | `Approx<T>` and Kleene `Truth` in the language | ING-O-8 |
| Entity naming | Provenance with history records (build123d's `Select.NEW`; FeatureScript's `qCreatedBy`) | Onshape FeatureScript queries | Typed queries over Anvil lineage, call-site identity from `BlockId`s, no positional access | ING-O-11 with Anvil's perturbation tests: share of queries stable under 16 perturbations ≥ 99% on golden products (target) |
| Incremental compilation | Red-green memoization with early cutoff (Salsa) | rust-analyzer | Salsa-style front-end stages inside Kiln; required signatures bound invalidation | Edit-replay corpus: re-check under 30 ms for a 2,000-line module (target) |
| Code generation | Cranelift for compile speed, LLVM for peak code | V8 TurboFan, LLVM | Wasm through Cranelift natively and browser engines on the web; reference interpreter | `ingot-bench`: within 1.5× of Rust natively, 3× in browsers (targets) |
| Memory management for pure languages | Perceus reference counting with reuse (PLDI 2021) | Koka | Perceus in the code generator | Peak semantic memory and time on `ingot-bench` against an arena baseline |
| Deterministic sandboxed execution | Wasm with fuel and canonical semantics (Wasmtime guide; Wasm 3.0 deterministic profile) | Wasmtime with NaN canonicalization and fuel | A NaN-free, growth-safe subset with compiled-in fuel, so no engine setting is needed | ING-O-1 across Tier 1 targets and browsers |
| Live programming with incomplete code | Typed holes with evaluation around them (Hazel) | Hazel | Holes from the error-resilient parser, evaluated around | ING-O-15 |
| Bidirectional editing | Trace-based program repair from output edits (Sketch-n-Sketch) | Sketch-n-Sketch (research); Onshape's dimension editing | Dependence and forward-mode derivatives for UIX edit plans | UIX's intent-match rate (D-UIX-15) |
| Lossless syntax trees | Red-green trees (Swift's libsyntax, rust-analyzer) | rust-analyzer with `rowan` | `rowan`, plus a block grammar for the CRDT | ING-O-2, ING-O-10; reparse of a 2,000-line file under 5 ms (target) |
| Collaborative structure | Movable tree CRDT (Kleppmann and colleagues), Fugue text | Loro | Ingot's grammar is designed for Loro's block tree (D-ING-18) | Kiln's merge corpus |
| Version resolution | PubGrub (conflict-driven, explanatory) | uv | PubGrub through ECO's resolver | ING-O-18: every failure explained |
| Language evolution | Editions with automated migration (Rust) | Cargo's automatic edition migration | Editions plus an IIR-equality check per migration | ING-O-19 |
| Feature dialogs from code | FeatureScript preconditions with annotations | Onshape | Typed signatures plus attributes | ING-O-20 |
| Sketch and constraint language | Constraint graphs over sketch primitives, as catalogued by SketchGraphs | Onshape's sketcher, whose sketches SketchGraphs extracted [unverified: source system] | Builder blocks of symbolic entities and `Equation` items solved by `anvil::solve_constraints` | ING-O-23: every constraint type in the sample expressible; ≥ 99% of converted sketches re-solve within tolerance (target) |
| Debugging | DAP with reverse execution (`supportsStepBack`, `stepBack`, `reverseContinue`) | Record-and-replay debuggers for native code [unverified: none opened] | Replay from Kiln's cache with reverse stepping, exact because evaluation is pure | ING-O-22 |

Deviation from the state of the art, stated plainly: Ingot does not use stack switching for suspension, because it is not available in every Tier 1 engine; it uses a state-machine transformation that costs some code size. Ingot does not use LLVM even though its code is about 14% faster than Cranelift's, because LLVM cannot target the browser at run time and compiles about ten times slower.

## Platform notes

| Risk or decision | Detail |
| --- | --- |
| One artifact everywhere | Ingot ships one Wasm module per package version for every target; only Wasmtime's precompiled form is per target. A divergence between targets is therefore an engine defect, and ING-O-1 finds it |
| Browsers | Generated modules use core WebAssembly with fixed-width 128-bit SIMD and nothing newer, which every Tier 1 browser runs [unverified: per-browser SIMD status not opened]. The page's Content Security Policy must allow `'wasm-unsafe-eval'`. Single-threaded browser builds run Ingot on the engine worker with fuel-sliced yielding at Kiln calls |
| No JIT on iPadOS | The reference interpreter runs Ingot there (Tier 2). A design behaves identically, more slowly; the interpreter's 15× target keeps feature overhead small next to operations |
| macOS hardened runtime | Wasmtime needs the JIT entitlement on macOS (PLT); Ingot inherits PLT's handling |
| Memory | Ingot modules use 32-bit memories. Large data stays in Kiln and crosses as handles, so the 4 GiB limit applies only to plain values of one feature call |
| Floating point | Generated code uses only correctly rounded basic operations and `detmath`; no target-specific fused multiply-add, flush-to-zero or excess precision |
| Paths and text | Source paths are repository-relative with `/`, NFC, LF line endings; the platform layer normalizes on load (PLT) |
| Air-gapped installs | std ships precompiled for every Tier 1 target; the compiler and interpreter are in every build; no network is needed to compile or evaluate |
| Accessibility | Diagnostics are plain text with spans, so screen readers announce them; the code panel's accessibility is UIX's |
| Tier 3 | Wasmtime with Cranelift where available, else Pulley or the interpreter; results stay out of shared caches until the determinism suite passes |

## Interfaces with other subsystems

### Provided

| To | What Ingot provides | Types |
| --- | --- | --- |
| Kiln (KLN) | Front-end stages as memoized queries; IIR with code hashes; static prefetch lists; compiled modules and the interpreter; Kiln call protocol with program order; literal overrides; failures as values; accumulators; recorded fuel; the block grammar for the live document | `Op`, `OpSite`, `Feature`, `Check` |
| Anvil (ANV) | `OpSite` from `BlockId` and call path (D-ANV-14); canonical `QueryPlan`s; role identities; GD&T attributes keyed by `EntityId`; `Tol` values for PMI | `Query`, `EntityId`, `Tol<T>` |
| Flux (FLX) | Generic `Field<D, V, A…>` types; `Expr<T, Out>` DAGs for forms, constitutive functions and analytic Fields; affine temperature with `.absolute()`; `Complex<Q>` and `im`; structural record results; `Approx<T>`, `Truth` and three-valued check outcomes | `Field`, `Quantity<D>`, `ErrorBound` |
| MEC | `feature`, `record`, builder blocks, symbolic constraints (replacing a separate `constraint` keyword), `family` over `Params<f>` with table literals and CSV headers, roles in queries, `Tol<T>` with fit codes, typed aspects for GD&T, `require` with severities. One signature per name, so MEC's two-corner `rect(p0, p1)` becomes `rect_between(p0, p1)` beside `rect(width, height, center:)` | `Feature`, `Tol<T>`, `Query`, `Check` |
| ELX | Builder blocks for `circuit { … }` with set-like accumulation; enums for variants; correlation groups on `Tol`; data modules as ordinary Ingot files with one item per block | `Tol<T>`, `Feature` |
| MFG, COV | Records, enums, `Map`, `Range` as interval type, `Decimal` for money, `require`, functions as templates | `Quantity<D>`, `Check` |
| UIX | Language service; semantic tokens; source map from `EntityId` to span; dialog metadata and handles; forward-mode derivatives for edit plans; minimal `SourcePatch`es; debugger views of intermediate Bodies | `SourceSpan`, `Feature` |
| AGT (`api`) | Diagnostics with machine-applicable fixes as `SourcePatch` lists; the formatter; doc comments and metadata for tool schemas; `ExternalText`; `CheckOutcome` fields | `Check`, `Feature` |
| ECO | Manifest language keys, lockfile `[language]` section, the module system, editions within the language, `ingot-bindgen` conventions, semantic-version rules for the Ingot interface | `Feature`, `Quantity<D>` |
| PLT | Compilation strategy; generated modules that pass PLT's validator; the interpreter for no-JIT targets | `PlatformClass` |

### Consumed

| From | What Ingot needs | Types |
| --- | --- | --- |
| Kiln (KLN) | Suspending scheduler with dynamic dependencies (D-KLN-1); front-end node keys by module and compiler behavior version; feature keys extended with code hashes and `OpSite`; the `OpSite` in every `OpKey` of an operation that names entities (see open question 13); caching of deterministic failures (D-KLN-6); overrides as input cells; `BlockId`s from the live document | `Op`, `ObjectId` |
| Anvil (ANV) | `anvil::resolve` as an operation over `QueryPlan`s with ranked fixes; role vocabularies; attribute side table; tangent rules and `shape_velocity`; `check_body` for tests | `Query`, `ResolveError`, `HistoryRecord`, `ErrorBound` |
| Flux (FLX) | Kernel IR for `Expr` DAGs; tangent and adjoint rules per operation; `ErrorBudget` totals for Field reductions | `Field`, `ErrorBudget` |
| PLT | `detmath` compiled for native and wasm32; `wasm-host` with Wasmtime and precompile caching; Pulley; the module validator; text normalization | `PlatformClass` |
| ECO | Registry, signing, PubGrub resolution, publish-time interface diff, browser bundles for components | Package |
| MEC | GD&T records and validators per dialect; `std::mech` features with declared roles | `Tol<T>`, `Part` |
| AGT | `SourcePatch`, `Severity`, `CheckOutcome`, stability ranking of fixes (D-AGT-8) | `Check` |

## Oracles

All oracles live under `oracles/ingot/` (protected). "Corpus" means the Ingot conformance corpus: std, the golden products, every registry package's tests and a generated set of random well-typed programs.

| Oracle | What it verifies | Pass criterion | Phase |
| --- | --- | --- | --- |
| ING-O-1 Conformance | Compiled code on every Tier 1 target and browser, and the interpreter, agree on values, failures, fuel and Kiln call sequences | Bit-identical on the whole corpus | 0 |
| ING-O-2 Round trip | Parse then print reproduces every byte, for valid and invalid inputs | Exact | 0 |
| ING-O-3 Parser fuzzing | No crash, no hang, bounded memory on arbitrary bytes | 10⁹ executions per release without failure | 0 |
| ING-O-4 Units | A seeded-error corpus of dimension, kind and affine mistakes, including degree-radian and rpm-hertz confusions | Every seeded error rejected with the expected code; no false rejection on the valid corpus | 0 |
| ING-O-5 Type system | Typing judgments on a curated corpus; soundness smoke test: well-typed random programs never hit an internal type failure | Zero internal failures | 0 |
| ING-O-6 Stack and depth | Deepest legal recursion runs on every engine; one deeper fails with `ING6302` everywhere | Identical outcome on every target | 0 |
| ING-O-7 Tolerances | Affine `Tol` limits against exact rational stacks; enclosures against 10⁶ sampled points per nonlinear case | Exact for linear; containment for nonlinear | 1 |
| ING-O-8 Truth | Comparisons of `Approx` values against exact references with injected bounds | Never `True` or `False` when the exact relation is the opposite | 1 |
| ING-O-9 Fixes | Every machine-applicable fix in the corpus compiles and removes its diagnostic | 100% | 1 |
| ING-O-10 Structural edits | Recorded GUI sessions produce minimal patches that keep comments and `BlockId`s | 100% | 1 |
| ING-O-11 Query lowering | Query syntax lowers to the canonical plan; plans for equal queries hash equal | Exact | 1 |
| ING-O-12 Drag specialization | Residual programs give the same outputs as full evaluation for the same overrides | Bit-identical on golden-product drag scripts | 1 |
| ING-O-13 Minimal re-evaluation | After scripted edits, the set of re-executed feature and Op nodes equals the reference set computed from code hashes and data dependence | Equal on 500 edits (shared with Kiln's minimality oracle) | 1 |
| ING-O-14 Code generator fuzzing | Differential fuzzing of random programs: interpreter versus compiled code, and optimized versus unoptimized IIR | No divergence per release | 1 |
| ING-O-15 Holes | Programs with random holes evaluate every hole-independent binding to the same value as the complete program | Exact | 1 |
| ING-O-16 Derivatives | Forward-mode derivatives against central differences on smooth programs; dependence sets against brute-force perturbation | Taylor order 2 ± 0.1; dependence exact | 1 |
| ING-O-17 Rust features | Macro output matches checked-in WIT and wrappers; wrapper signatures match WIT units | Exact | 1 |
| ING-O-18 Packages | Resolution explanations for every unsatisfiable fixture; two-major coexistence errors | Every failure explained; no silent choice | 1 |
| ING-O-19 Editions | Every migration preserves IIR and output hashes | 100% of the corpus | 2 |
| ING-O-20 Metadata | Every std feature has a dialog, docs and an evaluated example | Coverage 100% | 1 |
| ING-O-21 Service latency | Completion, hover and diagnostics on an edit-replay corpus | Within the stated targets at the 95th percentile | 1 |
| ING-O-22 Debugger | Stepping forward then backward returns identical frames; replay reports the same failure span as the original run | Exact | 2 |
| ING-O-23 Sketch expressiveness | A fixed SketchGraphs sample converts to Ingot sketch blocks that re-solve to the recorded geometry | Every constraint type expressible; ≥ 99% re-solve within tolerance (target) | 1 |

## Phasing

| Phase | Ingot deliverables | Gate contribution |
| --- | --- | --- |
| 0, foundations | Lexer, parser, lossless tree, formatter; dimension algebra and type checker for the core; IIR; reference interpreter; fuel; Kiln call protocol; determinism suite entries ING-O-1 to ING-O-6; compilation strategy benchmarks against prototypes | "Unit errors fail to compile" (contract gate) is ING-O-4; determinism suite includes ING-O-1 |
| 1, wedge | Wasm code generator with Perceus; `Tol`, `Approx`, `Truth`; queries; builder blocks and sketches; GD&T attachment; families and tables; modules, lockfile, PubGrub; metadata and docs; language service; tests and benchmarks; Rust features; drag specialization; holes; forward-mode derivatives | Golden products 1 and 2 build from std Ingot within the 2 s rebuild target |
| 2, mechanical depth | Debugger with reverse stepping; notebooks; reverse-mode derivatives; `dyn Trait`; first edition-migration machinery exercised on a pre-release edition; interpreter tuning for iPadOS | Golden products 3 and 4 |
| 3, product breadth | ELX data modules and circuit builders at scale; KCL importer; performance work for large data modules | Golden product 5 |
| 4, full multiphysics | Large symbolic forms (FLX coupling); compile-time limits tuned for physics packages | Golden product 6 |
| 5 and later | Proposed: a verified core (mechanized type soundness for the dimension and tolerance calculus), and a second independent implementation of the reference interpreter for certification work in aerospace and medical domains | Proposed golden products of MEC phases 5 and 6 |

## Open questions

1. **Kind granularity.** How many quantity kinds belong in std? Too few leaves torque-energy confusion possible; too many forces casts in physics code. Proposal: start with the four pairs named in "Dimensions" and add kinds only on evidence from user errors.
2. **Torque units.** D-ING-3 keeps newton metres for torque. mp-units describes Quincey's proposal to make the radian a base or complementary unit, which would change torque to J·rad⁻¹; its adoption status is [unverified]. Should Ingot track such a revision through an edition?
3. **Affine arithmetic cost at scale.** Affine forms grow with the number of sites a value depends on. Stacks over 10⁵ sites (large assemblies) may need symbol condensation, which trades exactness for size. The threshold and the reporting of condensation need measurement in phase 2.
4. **Stack switching.** If every Tier 1 engine supports Wasm stack switching, should Ingot replace its state-machine transformation? The decision depends on measured code size and speed.
5. **Interpreter or Pulley on iPadOS.** Phase 2 benchmarks decide; both are deterministic.
6. **Data modules for ELX.** ELX asks whether schematic and layout data should be Ingot files or a separate canonical format. This draft accepts Ingot files with one item per block, but very large layouts (10⁶ items) may parse too slowly; a binary sidecar keyed by `BlockId` is the fallback.
7. **Evaluation-world `Decimal`.** MFG's `Money<C>` needs exact decimal arithmetic. Is a fixed 10⁻⁹ resolution enough for every currency and pricing rule?
8. **Fragile anchors in agent output.** Should the compiler reject, rather than warn about, queries anchored only on `Ordinal` discriminators in protected branches?
9. **Literal sites under the CRDT.** Overrides key literals by `BlockId` and call path. When a concurrent edit splits a block during a drag, the override may lose its site; the drag then ends with a notice. Is that acceptable to UIX?
10. **Statistical defaults.** The default distribution for tolerance sites (normal, Cp = 1) is a convention. MFG may prefer process-specific defaults; that would make results depend on the process profile, which is correct but less predictable.
11. **Feature granularity in history.** Every `feature` call is a history entry and a Kiln node. std helpers that users never think of as features (`rect`, `fit`) are `fn`. The line is a judgment call per std function, and MEC, FLX and ELX should review the split before phase 1 freezes std.
12. **Matrices with per-row dimensions.** `Mat<R, C>` needs type-level lists of dimensions. The type checker supports them, but error messages for mismatched Jacobians need design work with FLX, which raised readability of `Field` types as a concern.
13. **Site in the `OpKey`.** Anvil hashes the `OpSite` into every `EntityId` (D-ANV-14), but Kiln's `OpKey` lists no site. Two calls with identical inputs at different sites would then share one cached result named for the first site. Proposal: Kiln includes the `OpSite` in the key of every operation that creates entities; to recover cross-design sharing, Anvil may later split naming into a cheap relabeling node over a site-free result. KLN and ANV should decide jointly.

## Contract change requests

1. **CCR-ING-1. Three-valued check outcomes.** Add `Undecided { reason, needed }` to `Check` outcomes and AGT's `CheckStatus`, supporting FLX's CCR-FLX-3. *Reason:* `Truth` makes undecidable comparisons explicit in the language, and checks must report them.
2. **CCR-ING-2. Add `Approx<T>` to the core types.** The contract defines `ErrorBound` for conversions and Fields but has no type for a plain value with a bound. *Reason:* measurements, Field reductions and component results all return bounded values, and one type keeps "every approximation states its error" checkable by the compiler.
3. **CCR-ING-3. `Tol<T>` semantics.** Record in section 5 that a feature parameter of type `T` accepts a `Tol<T>`, forwarding the tolerance and computing with the nominal (D-ING-4), and that `Tol` arithmetic is worst case with explicit statistics (D-ING-5). *Reason:* every tab writes toleranced parameters; one rule avoids divergent interpretations.
4. **CCR-ING-4. Syntax reference update.** Replace section 6's example with the canonical version at the top of this tab: roles instead of `top`, a tie-breaking selector, `Tol` forwarding, the material assigned before the stress solve that needs it, and a material property call instead of a bare `yield`. *Reason:* the contract's sketch relies on an ambient `yield` and a `top` selector that the query language does not define.
5. **CCR-ING-5. Crate list.** Add `ingot-codegen`, `ingot-service` and `ingot-bindgen` (with the proc-macro crate `ingot-macros`) under `core/`. *Reason:* compilation, tooling and bindings are distinct responsibilities with distinct dependencies (`wasm-host`, `kiln`).
6. **CCR-ING-6. Language behavior version in the lockfile.** Extend the cache key description in section 5 (`Op`) and Kiln's feature key with the language behavior version and code hashes. *Reason:* fuel costs and std numeric semantics are part of a feature's result (D-ING-16).
7. **CCR-ING-7. Angle as a base dimension, with torque in newton metres.** Record D-ING-3 in section 5's `Quantity<D>` entry. *Reason:* every tab computes with angles and torques, and the convention must be uniform.
8. **CCR-ING-8. One `Severity` type for checks.** Section 5's `Check` has a severity; define it once as `Error | Warning | Info`, used by Ingot's `require`, AGT's `CheckOutcome` and `Finding`, and MEC's rule tables. *Reason:* AGT, MEC and this tab each use a severity without a shared definition.
9. **CCR-ING-9. MEC's `constraint` keyword and `interface` keyword.** Replace them with ordinary functions over `Expr<T>` (D-ING-9) and records marked `#[interface]`. *Reason:* one mechanism for staged symbolic values and no second record kind; MEC's semantics are unchanged.
10. **CCR-ING-10. `OpSite` in Kiln keys.** Section 5 defines the `Op` cache key without the call site, while `EntityId` hashes the site. Add the `OpSite` to the key of operations that create entities, or split naming from computation (open question 13). *Reason:* without it, a cache hit can return entities named for another call site.

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
