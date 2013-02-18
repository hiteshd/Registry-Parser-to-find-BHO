
create sequence serial_executions;

create sequence serial_chrome;

create sequence serial_msie;

create sequence serial_mappings;

create table executions (
id bigint UNIQUE DEFAULT nextval('serial_executions'),
md5 text,
CONSTRAINT id_md5 PRIMARY KEY(id,md5)
);

create table chrome (
id bigint PRIMARY KEY DEFAULT nextval('serial_chrome'),
registry_key text,
bho_name text
);

create table msie (
id bigint PRIMARY KEY DEFAULT nextval('serial_msie'),
registry_key text,
bho_name text
);

create table mappings ( 
id bigint PRIMARY KEY DEFAULT nextval('serial_mappings'),
exec_id bigint references executions(id) ON UPDATE CASCADE ON DELETE CASCADE, 
chrome_id bigint references chrome(id) ON UPDATE CASCADE ON DELETE CASCADE,
msie_id bigint references msie(id) ON UPDATE CASCADE ON DELETE CASCADE
);

