# Ingot design language (ING)

Ingot is Crucible's design language: pure, strict and statically typed, with units, dimensions, tolerances, approximation error and geometric references as types, so unit and dimension errors never reach evaluation. A reference interpreter in the canonical class runs Ingot on every target, and every operation call becomes a node in Kiln's graph, named by a call-site identity derived from source text alone. The visual editor, the code editor and agents edit one lossless syntax tree, so every edit is a minimal, comment-preserving, mergeable source change.

## Scope and principles

### What this tab owns

| ING owns | Others own |
| --- | --- |
| Syntax, grammar, formatting, editions | Operation semantics and behavior versions (ANV, FLX) |
| Types: `Quantity<D>`, `Tol<T>`, `Approx<T>`, `Truth`, `Expr<T>`, records, enums, traits | `ErrorBound`, `ErrorBudget`, `CheckOutcome` shapes in `base`; `Field` (FLX) |
| `OpSite`; query syntax, lowering and the `Truth` rule for `where:` | `EntityId`, lineage and query resolution (ANV) |
| Evaluation semantics, `Failure` versus `Abort` in the language, limits | Scheduling, caching, labels and the determinism policy (KLN); mechanisms (PLT) |
| The interpreter, the IIR and the deferred code generator | The kernel IR and its back ends (FLX, `kernels`); the determinizer (PLT) |
| Check semantics, diagnostics and fixes | Release policy (KLN `repo`); the verifier (AGT) |
| Modules, manifest language keys, lockfile `[language]`, semantic-version rules | Registry and signing (ECO); lockfile storage (KLN) |
| Bindings and `#[ingot::feature]` | WIT worlds and capabilities (ECO) |
| Feature metadata and documentation | Dialog rendering and handles (UIX) |
| Language service, debugger, tests and benchmarks | Code panel and viewport (UIX); agent tools (AGT) |

| Crate (contract section 12) | Contents | Phase |
| --- | --- | --- |
| `ingot-syntax` | Lexer, block-local error-resilient parser, lossless tree, formatter, edition migrations | 0 |
| `ingot-types` | Name resolution, inference, dimension and tolerance algebra, traits, the diagnostics catalog | 0 |
| `ingot-ir` | The Ingot IR (IIR), lowering, `OpSite` derivation, the reference interpreter, differentiation | 0 |
| `ingot-bindgen`, `ingot-macros` | WIT bindings and the `#[ingot::feature]` macro | 1 |
| `ingot-service` | Language server, structural edits, test and benchmark runner; debugger and notebooks | 1, 2 |
| `ingot-codegen` | IIR to WebAssembly, entering only when justified (see "Execution") | 2 at the earliest |

Every Ingot crate is `forbid(unsafe_code)`.

### Design rules

1. **Pure.** No expression observes time, randomness, files, network, thread order, memory addresses or entity names. Randomness is an explicit keyed value.
2. **Strict and bounded.** Call by value, left to right. Every node ends in a value or a typed `Failure`; every Evaluation ends or aborts.
3. **Physics in types.** Dimensions, affine quantities, tolerances and approximation error are types.
4. **Geometry by provenance, names from text.** Code never holds an entity index. Call-site identities come from source text only.
5. **One program, three editors.** Every GUI action and agent edit is a minimal edit of the lossless tree.
6. **No privileged code.** std is ordinary Ingot; operations and Wasm components are reached through `extern` declarations anyone can write.
7. **Errors are values with fixes; the environment is never a value.** A `Failure` has a code, a reason, a location and typed fixes. An `Abort` is not a value.
8. **No macros.** Builder blocks, attributes and generics cover what macros would; code generation happens only outside the language.

**Decision D-ING-1:** Ingot is a pure, strict, expression-oriented language with immutable values, full type inference inside bodies, and required type signatures on every named function, feature and record. *Why:* signatures make each module type-check on its own, which bounds recompilation to the edited module and its dependents, and they generate dialogs and documentation; local inference keeps bodies short. *Rejected:* whole-program inference without signatures (errors appear far from causes); dynamic typing as in CadQuery and OpenSCAD (unit errors surface at run time or never); mutable variables (they break the dataflow lowering); lazy evaluation (costs and failures would depend on demand order, while Kiln already evaluates on demand at the level of nodes).

### The language at a glance

The canonical example of contract section 6:

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

Every construct is specified below. `thickness` arrives as a `Tol<Length>`: the body computes with the nominal, and `extrude` receives the tolerance and attaches it as PMI (D-ING-4). The web's edge is selected by the role that the rectangle's named `top` edge generates, never by rank. `stress` is an `Approx<Stress>` from a regularized maximum over a region away from the clamp, so the check returns a three-valued `Truth` (D-ING-7). Every entity is named from the call sites `outline`, `base`, `web`, `body` and `solid`, so the names survive any edit that keeps those bindings.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Canonical example | The contract section 6 example compiles and evaluates with the outcome kinds stated there | Any diagnostic or other outcome fails the oracle | ING-O-33 | 1 |
| Purity | No expression observes time, randomness, files, network, thread order, addresses or names | Not expressible in the language | ING-O-1, ING-O-30 | 0 |

## Lexical syntax and grammar

### Source text

| Aspect | Rule |
| --- | --- |
| Encoding | UTF-8 in NFC, normalized by the platform layer on load; non-NFC input that bypassed it fails with `ING0002` |
| Line endings | LF; CRLF is accepted and normalized by the formatter |
| Identifiers | Letters, digits and `_`, not starting with a digit; Unicode letters follow UAX #31 default identifiers [unverified]; `ING-L-MixedScript` flags mixed-script identifiers |
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
| Compound unit | `9.81[m/s^2]`, `200[W/(m*K)]`, `12[N*m]` | `Quantity<D>` |
| Temperature | `20degC`, `68degF` (points); `15K`, `5delta_degC` (differences) | `Temperature`, `TemperatureDifference` |
| Ratio | `5%`, `150ppm` | `Real` |
| Tolerance | `4mm ± 0.1mm`, `10mm ±(-0.1mm, +0.2mm)`, `1uH ± 20%` | `Tol<T>` |
| String | `"M6x1"`, `r"C:\raw"`, `"Rib {i}"`, `"{width:mm} plate"` | `String`; interpolating a quantity needs a unit |

A unit attaches to its number with no space, so `2in` is two inches and `2 in r` tests membership. The lexer takes the longest unit name, and letters that form no unit are an error (`ING0201`). A compound unit sits in brackets, and an exponent needs digits after `e`, so `1eV` is one electronvolt.

The unit table is closed per edition: SI base and derived units with SI prefixes, the radian, the accepted non-SI units (`min`, `h`, `L`, `t`, `bar`, `eV`, `deg`, `rev`, `arcmin`, `arcsec`, `degC`, `degF`, `degR`), US customary units (`in`, `ft`, `thou`, `lb`, `lbf`, `psi`, `ksi`) and the rotational named units of D-ING-3. Prefixes compose only where defined, so `ft` is never a femtotonne. Packages cannot add units; a domain unit such as the knot is a constant (`std::units::knot`). Canonical spellings are ASCII (`um`, `deg`, `degC`, `ohm`); the formatter rewrites `µm`, `°`, `°C`, `Ω` and `+-`, and `±` is the one non-ASCII token.

**Decision D-ING-2:** Every dimensional literal carries its unit, no file or package declares a default unit, and the compiler converts a literal to its SI value by exact rational arithmetic with one correct rounding. *Why:* a default unit makes a bare number mean different things in different files (KCL's documentation calls such a number "possibly any of them"), and exact conversion makes `25.4mm == 1in` hold bit for bit everywhere. *Rejected:* KCL's `defaultLengthUnit` (meaning depends on file context); multiplying by a floating-point factor (double rounding makes equal lengths unequal); a unitless zero accepted as any quantity (`0mm` is explicit).

### Grammar

The grammar is LL(1) after the lexer, except that `{` after an expression needs two tokens to separate a record literal, a block and a builder block. Builder blocks follow only a call's closing parenthesis, and the heads of `if`, `match` and `for` cannot end in a builder block or record literal unless parenthesized.

```ebnf
file         = { inner_attr } { item } ;
item         = { attr } [ visibility ] ( use_decl | fn_decl | feature_decl | extern_decl | record_decl
               | enum_decl | trait_decl | impl_decl | type_alias | kind_decl | let_decl ) | require_stmt ;
attr         = "#[" path [ "(" [ arg { "," arg } ] ")" ] "]" ;
inner_attr   = "#![" path [ "(" [ arg { "," arg } ] ")" ] "]" ;
visibility   = "pub" [ "(" "package" ")" ] ;
use_decl     = "use" use_tree ;
use_tree     = path [ "::" ( "{" use_tree { "," use_tree } [ "," ] "}" | "*" ) ] [ "as" ident ] ;
path         = ident { "::" ident } ;
kind_decl    = "kind" ident ( "=" | ":" ) dim_expr ;        (* "=" names a dimension; ":" a kind *)
fn_decl      = "fn" ident [ generics ] "(" [ params ] ")" "->" type [ where_clause ] block ;
feature_decl = "feature" ident [ generics ] "(" [ params ] ")" "->" type [ where_clause ] block ;
extern_decl  = "extern" ( "fn" | "feature" ) ident [ generics ] "(" [ params ] ")" "->" type ;
params       = param { "," param } [ "," ] ;
param        = { attr } ident ":" type [ "in" expr ] [ "=" expr ] ;   (* "in": checked range *)
record_decl  = "record" ident [ generics ] "{" [ field_list ] "}" ;
field_list   = field { "," field } [ "," ] ;
field        = { attr } ident ":" type [ "=" expr ] ;
enum_decl    = "enum" ident [ generics ] "{" variant { "," variant } [ "," ] "}" ;
variant      = { attr } ident [ "(" type { "," type } ")" | "{" field_list "}" ] ;
trait_decl   = "trait" ident [ generics ] [ ":" bounds ] "{" { fn_sig | assoc_type } "}" ;
impl_decl    = "impl" [ generics ] [ path "for" ] type [ where_clause ] "{" { fn_decl | type_alias } "}" ;
fn_sig       = "fn" ident [ generics ] "(" [ params ] ")" "->" type [ where_clause ] ;
assoc_type   = "type" ident [ ":" bounds ] ;
type_alias   = "type" ident [ generics ] "=" type ;
generics     = "<" ident [ ":" bounds ] [ "=" type ] { "," ident [ ":" bounds ] [ "=" type ] } ">" ;
bounds       = path [ "<" type_arg { "," type_arg } ">" ] { "+" path [ "<" type_arg { "," type_arg } ">" ] } ;
where_clause = "where" ident ":" bounds { "," ident ":" bounds } ;
let_decl     = "let" pattern [ ":" type ] "=" expr ;

type         = path [ "<" type_arg { "," type_arg } ">" ] | "[" type "]" | "(" [ type { "," type } ] ")"
               | "{" field_types "}" | "fn" "(" [ type { "," type } ] ")" "->" type | "impl" bounds ;
field_types  = ( ident ":" type | ".." type ) { "," ( ident ":" type | ".." type ) } [ "," ] ;
type_arg     = type | dim_expr ;
dim_expr     = dim_term { ( "*" | "/" ) dim_term } ;
dim_term     = ( ident | "1" | "(" dim_expr ")" ) [ "^" rational ] ;
rational     = [ "-" ] int_lit | "(" [ "-" ] int_lit "/" int_lit ")" ;

block        = "{" { stmt } [ expr ] "}" ;
stmt         = { attr } ( let_decl | require_stmt | expr ) ;
require_stmt = "require" expr { "," ident ":" expr } ;
expr         = pipe ;
pipe         = range_expr { "|>" postfix } ;                 (* right side must be a call *)
range_expr   = or_expr [ ( ".." | "..=" ) [ or_expr ] ] | ( ".." | "..=" ) or_expr ;
or_expr      = and_expr { "or" and_expr } ;
and_expr     = not_expr { "and" not_expr } ;
not_expr     = [ "not" ] cmp_expr ;
cmp_expr     = tol_expr { ( "==" | "!=" | "<" | "<=" | ">" | ">=" | "in" ) tol_expr } ;
tol_expr     = add_expr [ "±" ( add_expr | "(" add_expr "," add_expr ")" ) ] ;
add_expr     = mul_expr { ( "+" | "-" ) mul_expr } ;
mul_expr     = unary { ( "*" | "/" | "&" ) unary } ;
unary        = [ "-" | "+" ] power ;
power        = postfix [ "^" unary ] ;                       (* right-associative; -x^2 = -(x^2) *)
postfix      = primary { "." ident [ call_args [ block ] ] | call_args [ block ] | "[" expr "]" | "?" } ;
call_args    = "(" [ arg { "," arg } [ "," ] ] ")" ;
arg          = [ ident ":" ] expr | ".." expr ;               (* ..record spreads named arguments *)
primary      = literal | path | "(" expr { "," expr } ")" | "[" [ expr { "," expr } ] "]" | record_lit
               | map_lit | table_lit | if_expr | match_expr | for_expr | lambda | "try" expr | block ;
lambda       = "|" [ ident [ ":" type ] { "," ident [ ":" type ] } ] "|" expr ;
record_lit   = path "{" [ fields ] "}" | "{" fields "}" ;
fields       = ( ".." expr | ident ":" expr ) { "," ( ".." expr | ident ":" expr ) } [ "," ] ;
map_lit      = "[" expr "=>" expr { "," expr "=>" expr } [ "," ] "]" ;
table_lit    = "table" "{" ident { "|" ident } { row } "}" ;
row          = expr { "|" expr } ;                            (* one row per line *)
literal      = int_lit | real_lit | quantity_lit | percent_lit | string_lit | "true" | "false" ;
quantity_lit = ( int_lit | real_lit ) ( unit | "[" unit_expr "]" ) ;
unit_expr    = unit_term { ( "*" | "/" ) unit_term } ;
unit_term    = ( unit | "(" unit_expr ")" ) [ "^" rational ] ;
pattern      = "_" | ident | literal | range_pat | path [ "(" pattern { "," pattern } ")" ]
               | path "{" ident [ ":" pattern ] { "," ident [ ":" pattern ] } [ "," ".." ] "}"
               | "(" pattern { "," pattern } ")" | pattern "|" pattern ;
range_pat    = literal ( ".." | "..=" ) [ literal ] | ( ".." | "..=" ) literal ;
if_expr      = "if" expr block [ "else" ( if_expr | block ) ] ;
match_expr   = "match" expr "{" { pattern [ "if" expr ] "=>" expr "," } "}" ;
for_expr     = "for" pattern "in" expr block ;
```

Precedence, loosest first: `|>`; ranges; `or`; `and`; `not`; comparisons (chainable); `±`; `+` and `-`; `*`, `/` and `&`; unary minus; `^`; postfix. On Bodies and sets, `+`, `-` and `&` are union, difference and intersection. `x |> f(a)` means `f(x, a)`. Methods come only from `impl` blocks and traits, and a call followed by a block passes it as a builder (see "Builder blocks and sketches").

Named arguments may appear anywhere; positional arguments fill the remaining parameters in order, and `ING-L-NameArguments` asks for names after the second positional argument. Within one block each `let` name is unique (`ING1102`), so every statement has a stable textual name; inner blocks may shadow outer names. There is no ad hoc overloading: one name has one signature.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Lossless lexing and parsing | Every byte round-trips; malformed input becomes `ERROR` nodes inside its block | `ING0xxx` diagnostics; never a crash or hang | ING-O-2, ING-O-3 | 0 |
| Quantity literals | Exact rational conversion with one rounding; closed unit table per edition | `ING0201` unknown unit; `ING3001` dimension mismatch | ING-O-4 | 0 |
| Grammar | The EBNF above, with newline-terminated statements | `ING0xxx` with the expected tokens | ING-O-2, ING-O-5 | 0 |
| Unique statement names | One `let` name per block | `ING1102` with a rename fix | ING-O-5 | 0 |
