/* Lookup tables */

create table if not exists rule_types (
	type_id integer primary key,
	type text not null
);

create table if not exists sources (
	source_id integer primary key,
	name text not null,
	link text
);

create table if not exists tags (
	tag_id integer primary key,
	tag text not null
);

/* Data tables */

create table if not exists rules (
	rule_id integer primary key,
	type_id integer not null,
	cards integer not null,
	short text not null,
	full text not null,
	foreign key (type_id) references rule_types
);

create table if not exists variants (
	variant_id integer primary key,
	name text not null,
	cards integer not null,
	players integer not null,
	rounds integer not null,
	max_seen integer not null,
	wilds integer not null,
	source_id integer not null,
	foreign key (source_id) references sources
);

/* Data combination tables */

create table if not exists variant_rules (
	pair_id integer primary key,
	variant_id integer not null,
	rule_id integer not null,
	order integer not null,
	foreign key (variant_id) references variants,
	foreign key (rule_id) reference rules
);

create table if not exists variant_tags (
	pair_id integer primary key,
	variant_id integer not null,
	tag_id integer not null,
	foreign key (variant_id) references variants,
	foreign key (tag_id) references tags
);