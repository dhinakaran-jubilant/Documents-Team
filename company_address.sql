--
-- PostgreSQL database dump
--

\restrict zkdyMvcJy02gNKsynfuiIMtYqerm9Dc3a5Jk6z2i4Ro7jyeK8FAfnl9pe1dJxsy

-- Dumped from database version 18.1
-- Dumped by pg_dump version 18.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: company_addresses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.company_addresses (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    pan_number character varying(10),
    address text
);


ALTER TABLE public.company_addresses OWNER TO postgres;

--
-- Name: company_addresses_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.company_addresses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.company_addresses_id_seq OWNER TO postgres;

--
-- Name: company_addresses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.company_addresses_id_seq OWNED BY public.company_addresses.id;


--
-- Name: company_addresses id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company_addresses ALTER COLUMN id SET DEFAULT nextval('public.company_addresses_id_seq'::regclass);


--
-- Data for Name: company_addresses; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.company_addresses (id, name, pan_number, address) FROM stdin;
1	M/s. ROHIT ENTERPRISES	AVAPS3828F	No. 60, Ponnurangam Road, R.S Puram, Coimbatore - 641002. Tamil Nadu.
2	M/s. JUBILANT CAPITAL	AATFJ7144B	No. 187, West Ramalingam Road, R. S. Puram, Coimbatore – 641002, Tamil Nadu.
3	M/s. SURGE CAPITAL SOLUTIONS	AEOFS1548H	No. 187, West Ramalingam Road, R. S. Puram, Coimbatore – 641002, Tamil Nadu.
4	M/s. ASCEND SOLUTIONS	ACGFA3527L	No. 187, West Ramalingam Road, R. S. Puram, Coimbatore – 641002, Tamil Nadu.
5	M/s. GROWTH CAPITAL	AAWFG8669H	No. 60/129, East Bashyagarulu Road, R. S. Puram, Coimbatore – 641002, Tamil Nadu.
6	M/s. SHARVIL ENTERPRISES	AFLFS4726B	No. 5/6 4th Street, KV Colony, West Mambalam, Chennai - 600033, Tamil Nadu.
7	M/s. PRO MAX CAPITAL	AOBPP5676A	No 18/571 H, 2nd floor, Federal Bank Building, Athani, Nedumbassery P O, Ernakulam - 683585, Kerala.
8	Mr. S. SUDHAKAR	AVAPS3828F	S/o. RM. Sivaraman, No. 60, Ponnurangam Road, R. S. Puram, Coimbatore - 641002, Tamil Nadu.
9	Mrs. SUDHAKAR NIRMALA	ADDPN6171H	W/o. Sudhakar, No. 60, Ponnurangam Road West, R. S. Puram, Coimbatore – 641002, Tamil Nadu.
10	M/s. FORTUNE ENTERPRISES	AAJFF3001D	No. 187, West Ramalingam Road, R. S. Puram, Coimbatore – 641002, Tamil Nadu.
11	Mr. S. BALAKRISHNAN	BEQPB7729J	S/o. RM. Subramanian, No. 5, 5th Cross Street, Gnanaprakasam Nagar, Pondicherry – 605008.
12	M/s. EASY CREDIT SOLUTION	AAJFE4246P	No. 1/A Punniyakodi Street, R. S. Puram, Coimbatore - 641002, Tamil Nadu.
13	M/s. NEXUS CAPITAL	AAWFN2422K	No. 32, 6th Floor, Ambika Complex, NSK Salai, Kodambakkam, Chennai – 600024, Tamil Nadu.
14	M/s. SRI GURUDEV ENTERPRISES	AAHPJ1457F	No. 45/36, Strotten Muthu’s Mudali Street, Golden Arch Complex, Chennai - 600079, Tamil Nadu.
15	Mr. SENTHIL VADIVEL A J	ABUPS8845E	S/o. A. Jayaseelan, No. 1/A - Punniyakodi Street, R. S. Puram, Coimbatore - 641002, Tamil Nadu.
16	Mrs. SUDHAKAR NIRMALA	ADDPN6171H	W/o. S. Sudhakar, No. 60, Ponnurangam Road West, R. S. Puram, Coimbatore – 641002, Tamil Nadu.
17	M/s. MAPS ENTERPRISES	AAKPK7110R	No. 45/36 Strotten Muthia Mudali Street, Golden Arch Complex 2 nd floor, Sowcarpet , Chennai – 600079, Tamil Nadu.
18	M/r. C A  PRASANTH	BHIPP9137P	No. 14, Vijaya Villa, Srinivasa Avenue Road, Raja Annamalai Puram, Chennai – 600028, Tamil Nadu.
19	Mr. C. VAITHYALINGAM	AASPV5447L	S/o. Chinnan, No. 19/8 , Kirubasankari Street, West Mambalam, Chennai - 600033, Tamil Nadu.
20	Mr. VEERAPPAN MARUDHAMANI HUF	MARUDHAMAN	S/o. Marudhamani, No. 18, Swaraj Bhavan S1, 2nd Floor, 3rd Cross Street, CIT Nagar, Chennai – 600035, Tamil Nadu.
21	M/s. SATHYAM CREDIT SOLUTION	AEKFS9788M	No. 152-A, SPN house, Greenways Road, R.A puram (Next to Greenways Road Railway Station) Chennai - 600028, Tamil Nadu.
22	Mrs. S. BHARATHI	FYFPS9552H	W/o. Subramaniyan, Old No. 11/1, New No. 24, 1st Floor, Teachers Colony, Royapettah, Chennai - 600014, Tamil Nadu.
23	Mrs. SINGARAVALLI	\N	W/o. C Anand, No.24, First Floor,Teachers Colony, V.M Street,Royapettah, Chennai– 600014, Tamil Nadu.
24	M/s. ROHIT ENTERPRISES	AVAPS3828F	No.60, Ponnurangam Road, R.S Puram, Coimbatore - 641002. Tamil Nadu.
25	Mr. J. SENTHIL VADIVEL HUF	AAEHJ2404D	S/o. A. Jayaseelan, No. 1/A - Punniyakodi Street, R.S. Puram, Coimbatore – 641002, Tamil Nadu.
26	Mr. DINESH HUF	AAJHD9488G	No. 466, Sri Balaje Pharmaceuticals, Cross Cut Road, Gandhipuram, Coimbatore – 641012, Tamil Nadu.
27	Mr. SUDHAKAR SIVARAMAN (HUF)	AALHS5661N	S/o. RM. Sivaraman, No.- 60, Ponnurangam Road, RS Puram, Coimbatore - 641002, Tamil  Nadu.
28	Mrs. R. VANAJA	BEUPV2515N	No. 14, Srinivasa Avenue Road, Raja Annamalai Puram Chennai -600028, Tamil Nadu.
29	Mrs. B. VRIDDHAMBAL	ANIPV8396B	No.5, 5th Cross Street, Gnanaprakasam Nagar, Pondicherry – 605008.
30	Mr. S. KRISH SUNIL DUSEJA	ISAPD8552C	S/o. Sunil Gopichand Duseja, No. 7, GeeGee Villa, Kasturi Estate 2ND Street, Aswenee Soundra Hospital, Cathedral Road, Gopalapuram, Chennai - 600086, Tamil Nadu.
31	Mrs. B. SUNDARAVALLI	AVAPS7862D	W/o. Balakrishnan, No. 466, No. 27, Setnarayanadas Layout, Ponnian Street, Ram Nagar, Coimbatore - 641009, Tamil Nadu.
32	M/s. SREE KESARIYA INVESTMENTS	AAFPJ8749Q	No. 30, Thirupalli Street, 1st Floor, Chennai - 600079, Tamil Nadu.
33	Mr. B. Dinesh	AJKPD3863D	No. 466, Sri Balaje Pharmaceuticals, Cross Cut Road, Gandhipuram, Coimbatore – 641012, Tamil Nadu.
34	Mr. A. MATHESWARAN	FCQPM8453L	S/o. Anbalagan, No.- 115, Pudukkottai Road, Aranthangi, Pudukkottai – 614616, Tamil Nadu.
35	M/s. AADIT ENTERPRISES	AOBPP5676A	Building No. 2/96 A1, Karippayil Road, Rajagiri PO, Kalamassery – 683104, Kerala.
36	Mrs. S. KAVITHA	AAKPK1518P	W/o. Senthil Vadivel, No. 1A, Punniyakodi Muthaliyar Street, Coimbatore south, Coimbatore - 641002, Tamil Nadu.
37	M/s. A SQUARE ENTERPRISES	ACLFA2520L	No. 187, Ramalingam Road West, R. S. Puram, Coimbatore – 641002, Tamil Nadu.
38	M/s. AS ENTERPRISES (Pan No: ACJFA6272B)	ACJFA6272B	No. 187, West Ramalingam Road, R. S. Puram, Coimbatore – 641002, Tamil Nadu.
39	M/s. JANANI ASSOCIATES	HYFPS3517C	No. 48, Thaniyur Saliya Street, koranad, Mayiladuthurai - 609001, Tamil Nadu.
40	M/s. NEW GROWTH	AATFN6880E	No. 52, Manickam Street, Vepery, Chennai - 600007, Tamil Nadu.
41	M/s. FINOVA CAPITAL	AAKFF3257F	No. 27/6-A1, 1ST Floor, Padayatil Bidg, Near Home Science College, Angamaly South, Ernakulam - 683573, Kerala.
42	M/s. JAY ENTERPRISES	BBZPJ7104H	No. 1A, Punniyakodi Muthaliyar Street, Coimbatore south, Coimbatore - 641002, Tamil Nadu.
43	M/s. ARCHANA ENTERPRISES	AAHPJ1586F	No. 30, Vinayaga Maistry Street, Sowcarpet, Chennai - 600079, Tamil Nadu.
44	M/s. PERFECT  TRADERS. (Pan. No. AASFP0685J)	AASFP0685J	No. 132, SS Tower, Kodambakkam high road, Nungambakkam, Chennai -600034, Tamil Nadu.
45	M/s. PROPEL ENTERPRISES	\N	No. 5, Sriram Nagar South, B1, Ground Floor, Krithika Apartment, Alwarpet, Chennai - 600018, Tamil Nadu.
46	M/s. SHANTIKAMAL ENTERPRISES (Pan No. ARNPS7974B)	ARNPS7974B	No.30, Vinayaga Maistry Street, Sowcarpet, Chennai - 600079.
47	Mrs. S. Nandhini	CGYPN0581K	D/o. Sureshkumar, No. 3/C, Novel Residency , 9, Pattabiraman Pillai Street, Thennur, Tiruchirappalli – 620017, Tamil Nadu.
48	M/s. MAYILON VENTURES	ACFFM9372E	No. 32 , 4th Floor Ambika Complex , NSK Salai , Kodambakkam , Chennai – 600024, Tamil Nadu.
49	Mrs. S. RAJAPRIYA	BWUPR4114B	W/o. S. Sivaraman, No. 60, West Ponnurangam Road, R. S. Puram, Coimbatore – 641002, Tamil Nadu.
\.


--
-- Name: company_addresses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.company_addresses_id_seq', 49, true);


--
-- Name: company_addresses company_addresses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company_addresses
    ADD CONSTRAINT company_addresses_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

\unrestrict zkdyMvcJy02gNKsynfuiIMtYqerm9Dc3a5Jk6z2i4Ro7jyeK8FAfnl9pe1dJxsy

