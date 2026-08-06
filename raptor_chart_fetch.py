#!/usr/bin/env python3
"""
RAPTOR Chart Fetch v3.0 — GitHub Actions
Riscrittura secondo il pattern raptor-leva/scannerv2: un file JSON per ticker
in data/charts/{TICKER}.json + data/charts/index.json, con indicatori
precalcolati server-side (stessa logica esatta di raptor_fetch.py, per
restare coerenti con i segnali mostrati in tabella).

Novità v3.0:
- Niente più raptor_chart.json monolitico (7,9 MB) scaricato per intero
  dal browser: ogni pagina scarica solo il file del ticker che apre.
- KAMA/SAR/AO/RSI/ER/Baffetti/Segnale calcolati qui in Python su TUTTA la
  serie storica (array, non solo ultimo valore) — il browser non deve più
  ricalcolare nulla per disegnare grafico, marker e storia segnali.
- Renko (brick adattivo su ATR 14) calcolato server-side.
- Fix: rimosso ticker duplicato EIMI.MI dall'universo.
"""

import json, time, datetime, os, math
import yfinance as yf

# ── Modello ML per suggerimento uscita (allenato offline, solo inferenza qui) ──
try:
    import joblib
    _ML_EXIT = joblib.load(os.path.join(os.path.dirname(__file__), 'models_exit.joblib'))
except Exception as _e:
    print(f"ATTENZIONE: modello ML uscita non caricato ({_e}) — suggerimento uscita disattivato")
    _ML_EXIT = None

# ═══════════════════════════════════════════════════════
#  TICKER LIST (stessa dell'universo v2, EIMI.MI deduplicato)
# ═══════════════════════════════════════════════════════
TICKERS_RAW = [{"y":"IAEX.AS","t":"IAEX"},{"y":"TOF.AS","t":"TOF"},{"y":"18MN.DE","t":"18MN"},{"y":"7USH.DE","t":"7USH"},{"y":"CBUH.DE","t":"CBUH"},{"y":"CEB1.DE","t":"CEB1"},{"y":"CEB4.DE","t":"CEB4"},{"y":"GXDW","t":"GXDW"},{"y":"DBZB.DE","t":"DBZB"},{"y":"EUNY.DE","t":"EUNY"},{"y":"FTGM.DE","t":"FTGM"},{"y":"IBC5.DE","t":"IBC5"},{"y":"IBCJ.DE","t":"IBCJ"},{"y":"IQQ9.DE","t":"IQQ9"},{"y":"IQQF.DE","t":"IQQF"},{"y":"IS04.DE","t":"IS04"},{"y":"IS3C.DE","t":"IS3C"},{"y":"IS3N.DE","t":"IS3N"},{"y":"IS3U.DE","t":"IS3U"},{"y":"ISPA.DE","t":"ISPA"},{"y":"IUSQ.DE","t":"IUSQ"},{"y":"IUSS.DE","t":"IUSS"},{"y":"LCUJ.DE","t":"LCUJ"},{"y":"MJMT.DE","t":"MJMT"},{"y":"QDVA.DE","t":"QDVA"},{"y":"SPP5.DE","t":"SPP5"},{"y":"SPYX.DE","t":"SPYX"},{"y":"SXR1.DE","t":"SXR1"},{"y":"SXRT.DE","t":"SXRT"},{"y":"SXRU.DE","t":"SXRU"},{"y":"SXRW.DE","t":"SXRW"},{"y":"VGWE.DE","t":"VGWE"},{"y":"VUKG.DE","t":"VUKG"},{"y":"XBAS.DE","t":"XBAS"},{"y":"XCS3.DE","t":"XCS3"},{"y":"XCS4.DE","t":"XCS4"},{"y":"XD9E.DE","t":"XD9E"},{"y":"XD9U.DE","t":"XD9U"},{"y":"XDEM.DE","t":"XDEM"},{"y":"XESD.DE","t":"XESD"},{"y":"XGIN.DE","t":"XGIN"},{"y":"XMKA.DE","t":"XMKA"},{"y":"XPQP.DE","t":"XPQP"},{"y":"XWEM.DE","t":"XWEM"},{"y":"F701.F","t":"F701"},{"y":"F702.F","t":"F702"},{"y":"F703.F","t":"F703"},{"y":"IUSN.F","t":"IUSN"},{"y":"IVAI.MI","t":"IVAI"},{"y":"IVDF.DE","t":"IVDF"},{"y":"NQSE.F","t":"NQSE"},{"y":"NTSZ.DE","t":"NTSZ"},{"y":"IEFM.L","t":"IEFM"},{"y":"A01U.MI","t":"A01U"},{"y":"ACT20.MI","t":"ACT20"},{"y":"ACT60.MI","t":"ACT60"},{"y":"ACTEQ.MI","t":"ACTEQ"},{"y":"ADLU.MI","t":"ADLU"},{"y":"AEGE.MI","t":"AEGE"},{"y":"AGEB.MI","t":"AGEB"},{"y":"AGED.MI","t":"AGED"},{"y":"AGGH.MI","t":"AGGH"},{"y":"AI4UJ.MI","t":"AI4UJ"},{"y":"AIAA.MI","t":"AIAA"},{"y":"AIAI.MI","t":"AIAI"},{"y":"AICU.MI","t":"AICU"},{"y":"AIGA.MI","t":"AIGA"},{"y":"AIGC.MI","t":"AIGC"},{"y":"AIGE.MI","t":"AIGE"},{"y":"AIGG.MI","t":"AIGG"},{"y":"AIGI.MI","t":"AIGI"},{"y":"AIGL.MI","t":"AIGL"},{"y":"AIGO.MI","t":"AIGO"},{"y":"AIGP.MI","t":"AIGP"},{"y":"AIGS.MI","t":"AIGS"},{"y":"AINF.MI","t":"AINF"},{"y":"AIQE.MI","t":"AIQE"},{"y":"ALAT.MI","t":"ALAT"},{"y":"ALUM.MI","t":"ALUM"},{"y":"ANAU.MI","t":"ANAU"},{"y":"AQWA.MI","t":"AQWA"},{"y":"ARMI.MI","t":"ARMI"},{"y":"ARMR.MI","t":"ARMR"},{"y":"ASRD.MI","t":"ASRD"},{"y":"AT1.MI","t":"AT1"},{"y":"AUCO.MI","t":"AUCO"},{"y":"AUHEUA.MI","t":"AUHEUA"},{"y":"BATT.MI","t":"BATT"},{"y":"BBTR.MI","t":"BBTR"},{"y":"BCHN.MI","t":"BCHN"},{"y":"BENE.MI","t":"BENE"},{"y":"BIODV.MI","t":"BIODV"},{"y":"BIOT.MI","t":"BIOT"},{"y":"BKCH.MI","t":"BKCH"},{"y":"BLTH.MI","t":"BLTH"},{"y":"BNK.MI","t":"BNK"},{"y":"BNKE.MI","t":"BNKE"},{"y":"BOTZ.MI","t":"BOTZ"},{"y":"BRENT.MI","t":"BRENT"},{"y":"BRES.MI","t":"BRES"},{"y":"BRIJ.MI","t":"BRIJ"},{"y":"BRND.MI","t":"BRND"},{"y":"BRNT.MI","t":"BRNT"},{"y":"BSRIC.MI","t":"BSRIC"},{"y":"BT27.MI","t":"BT27"},{"y":"BTC.MI","t":"BTC"},{"y":"BTECH.MI","t":"BTECH"},{"y":"BTECJ.MI","t":"BTECJ"},{"y":"BTP10.MI","t":"BTP10"},{"y":"BUG.MI","t":"BUG"},{"y":"C40.MI","t":"C40"},{"y":"CAHEUA.MI","t":"CAHEUA"},{"y":"CARB.MI","t":"CARB"},{"y":"CAUT.MI","t":"CAUT"},{"y":"CBSUSA.MI","t":"CBSUSA"},{"y":"CCEUAS.MI","t":"CCEUAS"},{"y":"CCUSAS.MI","t":"CCUSAS"},{"y":"CHIP.MI","t":"CHIP"},{"y":"CHM.MI","t":"CHM"},{"y":"CIBR.MI","t":"CIBR"},{"y":"CIT.MI","t":"CIT"},{"y":"CITE.MI","t":"CITE"},{"y":"CITY.MI","t":"CITY"},{"y":"CLIP.MI","t":"CLIP"},{"y":"CLOU.MI","t":"CLOU"},{"y":"CMOC.MI","t":"CMOC"},{"y":"CMOD.MI","t":"CMOD"},{"y":"CMOE.MI","t":"CMOE"},{"y":"CN1.MI","t":"CN1"},{"y":"CO2.MI","t":"CO2"},{"y":"COCO.MI","t":"COCO"},{"y":"COFF.MI","t":"COFF"},{"y":"COMF.MI","t":"COMF"},{"y":"COMH.MI","t":"COMH"},{"y":"COMO.MI","t":"COMO"},{"y":"COPA.MI","t":"COPA"},{"y":"COPM.MI","t":"COPM"},{"y":"COPR.MI","t":"COPR"},{"y":"COPX.MI","t":"COPX"},{"y":"CORN.MI","t":"CORN"},{"y":"COTN.MI","t":"COTN"},{"y":"CROP.MI","t":"CROP"},{"y":"CRRY.MI","t":"CRRY"},{"y":"CRUD.MI","t":"CRUD"},{"y":"CSBGE7.MI","t":"CSBGE7"},{"y":"CSBGU3.MI","t":"CSBGU3"},{"y":"CSBGU7.MI","t":"CSBGU7"},{"y":"CSCA.MI","t":"CSCA"},{"y":"CSEMAS.MI","t":"CSEMAS"},{"y":"CSMIB.MI","t":"CSMIB"},{"y":"CSNDX.MI","t":"CSNDX"},{"y":"CSPXJ.MI","t":"CSPXJ"},{"y":"CSSPX.MI","t":"CSSPX"},{"y":"CSUS.MI","t":"CSUS"},{"y":"CSUSS.MI","t":"CSUSS"},{"y":"CTEK.MI","t":"CTEK"},{"y":"CURE.MI","t":"CURE"},{"y":"CWE.MI","t":"CWE"},{"y":"CYBO.MI","t":"CYBO"},{"y":"CYBR.MI","t":"CYBR"},{"y":"DAPP.MI","t":"DAPP"},{"y":"DEFS.MI","t":"DEFS"},{"y":"DEMR.MI","t":"DEMR"},{"y":"DFND.MI","t":"DFND"},{"y":"DFNS.MI","t":"DFNS"},{"y":"DGTL.MI","t":"DGTL"},{"y":"DISW.MI","t":"DISW"},{"y":"DJE.MI","t":"DJE"},{"y":"DMAT.MI","t":"DMAT"},{"y":"DOCT.MI","t":"DOCT"},{"y":"DPAY.MI","t":"DPAY"},{"y":"DRVE.MI","t":"DRVE"},{"y":"DXJF.MI","t":"DXJF"},{"y":"EALU.MI","t":"EALU"},{"y":"EBIZ.MI","t":"EBIZ"},{"y":"EBRT.MI","t":"EBRT"},{"y":"EBUY.MI","t":"EBUY"},{"y":"ECAR.MI","t":"ECAR"},{"y":"ECEH.MI","t":"ECEH"},{"y":"ECO.MI","t":"ECO"},{"y":"ECOF.MI","t":"ECOF"},{"y":"ECOM.MI","t":"ECOM"},{"y":"ECOP.MI","t":"ECOP"},{"y":"ECR1.MI","t":"ECR1"},{"y":"ECRD.MI","t":"ECRD"},{"y":"ECRN.MI","t":"ECRN"},{"y":"ECRP3.MI","t":"ECRP3"},{"y":"ECTN.MI","t":"ECTN"},{"y":"EDOC.MI","t":"EDOC"},{"y":"EEA.MI","t":"EEA"},{"y":"EEIA.MI","t":"EEIA"},{"y":"EENG.MI","t":"EENG"},{"y":"EFCM.MI","t":"EFCM"},{"y":"EGEHE.MI","t":"EGEHE"},{"y":"EGOV.MI","t":"EGOV"},{"y":"EHYA.MI","t":"EHYA"},{"y":"EIMI.MI","t":"EIMI"},{"y":"EIMT.MI","t":"EIMT"},{"y":"ELCR.MI","t":"ELCR"},{"y":"EM1015.MI","t":"EM1015"},{"y":"EM35.MI","t":"EM35"},{"y":"EM710.MI","t":"EM710"},{"y":"EMGH.MI","t":"EMGH"},{"y":"EMI.MI","t":"EMI"},{"y":"EMOVE.MI","t":"EMOVE"},{"y":"EMOVJ.MI","t":"EMOVJ"},{"y":"EMQQ.MI","t":"EMQQ"},{"y":"ENCO.MI","t":"ENCO"},{"y":"ENERW.MI","t":"ENERW"},{"y":"ENGS.MI","t":"ENGS"},{"y":"ENIK.MI","t":"ENIK"},{"y":"ENRG.MI","t":"ENRG"},{"y":"ENTR.MI","t":"ENTR"},{"y":"EPRA.MI","t":"EPRA"},{"y":"EPRE.MI","t":"EPRE"},{"y":"EROX.MI","t":"EROX"},{"y":"ESGO.MI","t":"ESGO"},{"y":"ESOY.MI","t":"ESOY"},{"y":"ESPO.MI","t":"ESPO"},{"y":"ESPY.MI","t":"ESPY"},{"y":"EST.MI","t":"EST"},{"y":"ESUG.MI","t":"ESUG"},{"y":"ETFCRP.MI","t":"ETFCRP"},{"y":"EUC.MI","t":"EUC"},{"y":"EUES.MI","t":"EUES"},{"y":"EWAT.MI","t":"EWAT"},{"y":"EXS1.MI","t":"EXS1"},{"y":"EXXY.MI","t":"EXXY"},{"y":"EZNC.MI","t":"EZNC"},{"y":"FAMAMW.MI","t":"FAMAMW"},{"y":"FAMMAI.MI","t":"FAMMAI"},{"y":"FAMMWF.MI","t":"FAMMWF"},{"y":"FAMMWS.MI","t":"FAMMWS"},{"y":"FAMTEL.MI","t":"FAMTEL"},{"y":"FAMWCS.MI","t":"FAMWCS"},{"y":"FCRU.MI","t":"FCRU"},{"y":"FGEA.MI","t":"FGEA"},{"y":"FINSW.MI","t":"FINSW"},{"y":"FINX.MI","t":"FINX"},{"y":"FLUSA.MI","t":"FLUSA"},{"y":"FLXI.MI","t":"FLXI"},{"y":"FLXT.MI","t":"FLXT"},{"y":"FLXU.MI","t":"FLXU"},{"y":"FMI.MI","t":"FMI"},{"y":"FOFD.MI","t":"FOFD"},{"y":"FOO.MI","t":"FOO"},{"y":"FOOD.MI","t":"FOOD"},{"y":"FUSU.MI","t":"FUSU"},{"y":"GAGG.MI","t":"GAGG"},{"y":"GAGH.MI","t":"GAGH"},{"y":"GAS.MI","t":"GAS"},{"y":"GASRI.MI","t":"GASRI"},{"y":"GCLE.MI","t":"GCLE"},{"y":"GCVE.MI","t":"GCVE"},{"y":"GDIG.MI","t":"GDIG"},{"y":"GDX.MI","t":"GDX"},{"y":"GDXJ.MI","t":"GDXJ"},{"y":"GENDEE.MI","t":"GENDEE"},{"y":"GLUG.MI","t":"GLUG"},{"y":"GLUX.MI","t":"GLUX"},{"y":"GNOM.MI","t":"GNOM"},{"y":"GOAI.MI","t":"GOAI"},{"y":"GOVA.MI","t":"GOVA"},{"y":"GRC.MI","t":"GRC"},{"y":"GRCTB.MI","t":"GRCTB"},{"y":"GREAL.MI","t":"GREAL"},{"y":"GSCE.MI","t":"GSCE"},{"y":"GSM.MI","t":"GSM"},{"y":"HDRO.MI","t":"HDRO"},{"y":"HEAL.MI","t":"HEAL"},{"y":"HECB.MI","t":"HECB"},{"y":"HERU.MI","t":"HERU"},{"y":"HGAE.MI","t":"HGAE"},{"y":"HIDIJ.MI","t":"HIDIJ"},{"y":"HLT.MI","t":"HLT"},{"y":"HLTW.MI","t":"HLTW"},{"y":"HMXJ.MI","t":"HMXJ"},{"y":"HNSC.MI","t":"HNSC"},{"y":"HPNA.MI","t":"HPNA"},{"y":"HSTE.MI","t":"HSTE"},{"y":"HTWO.MI","t":"HTWO"},{"y":"HUCB.MI","t":"HUCB"},{"y":"HUST.MI","t":"HUST"},{"y":"HYDE.MI","t":"HYDE"},{"y":"HYGN.MI","t":"HYGN"},{"y":"HYLD.MI","t":"HYLD"},{"y":"IAPD.MI","t":"IAPD"},{"y":"IBZL.MI","t":"IBZL"},{"y":"ICBR.MI","t":"ICBR"},{"y":"IEAA.MI","t":"IEAA"},{"y":"IEGS.MI","t":"IEGS"},{"y":"IEMB.MI","t":"IEMB"},{"y":"IEMO.MI","t":"IEMO"},{"y":"IJPE.MI","t":"IJPE"},{"y":"IMIB.MI","t":"IMIB"},{"y":"INDG.MI","t":"INDG"},{"y":"INDGW.MI","t":"INDGW"},{"y":"INDI.MI","t":"INDI"},{"y":"INDO.MI","t":"INDO"},{"y":"INF1A.MI","t":"INF1A"},{"y":"INFU.MI","t":"INFU"},{"y":"INQQ.MI","t":"INQQ"},{"y":"INS.MI","t":"INS"},{"y":"ISAC.MI","t":"ISAC"},{"y":"ISAG.MI","t":"ISAG"},{"y":"ISPY.MI","t":"ISPY"},{"y":"ITBL.MI","t":"ITBL"},{"y":"IU0E.MI","t":"IU0E"},{"y":"IUSE.MI","t":"IUSE"},{"y":"IWDE.MI","t":"IWDE"},{"y":"IWMO.MI","t":"IWMO"},{"y":"IWVL.MI","t":"IWVL"},{"y":"JEDI.MI","t":"JEDI"},{"y":"JRGE.MI","t":"JRGE"},{"y":"JU13.MI","t":"JU13"},{"y":"KARS.MI","t":"KARS"},{"y":"KOR.MI","t":"KOR"},{"y":"KRBN.MI","t":"KRBN"},{"y":"KWBE.MI","t":"KWBE"},{"y":"LABL.MI","t":"LABL"},{"y":"LAFRI.MI","t":"LAFRI"},{"y":"LCCN.MI","t":"LCCN"},{"y":"LEAD.MI","t":"LEAD"},{"y":"LGUS.MI","t":"LGUS"},{"y":"LINXB.MI","t":"LINXB"},{"y":"LITM.MI","t":"LITM"},{"y":"LITU.MI","t":"LITU"},{"y":"LOCK.MI","t":"LOCK"},{"y":"LTAM.MI","t":"LTAM"},{"y":"LVO.MI","t":"LVO"},{"y":"MACV.MI","t":"MACV"},{"y":"MAGR.MI","t":"MAGR"},{"y":"MATW.MI","t":"MATW"},{"y":"MCHN.MI","t":"MCHN"},{"y":"MCHT.MI","t":"MCHT"},{"y":"META.MI","t":"META"},{"y":"METAA.MI","t":"METAA"},{"y":"METAJ.MI","t":"METAJ"},{"y":"METE.MI","t":"METE"},{"y":"METL.MI","t":"METL"},{"y":"MILL.MI","t":"MILL"},{"y":"MLPS.MI","t":"MLPS"},{"y":"MODR.MI","t":"MODR"},{"y":"MTAV.MI","t":"MTAV"},{"y":"MTVS.MI","t":"MTVS"},{"y":"NATO.MI","t":"NATO"},{"y":"NCLR.MI","t":"NCLR"},{"y":"NGAS.MI","t":"NGAS"},{"y":"NICK.MI","t":"NICK"},{"y":"NRJC.MI","t":"NRJC"},{"y":"NTSG.MI","t":"NTSG"},{"y":"NUCL.MI","t":"NUCL"},{"y":"OCEAN.MI","t":"OCEAN"},{"y":"OIH.MI","t":"OIH"},{"y":"OVER.MI","t":"OVER"},{"y":"PAVE.MI","t":"PAVE"},{"y":"PCOM.MI","t":"PCOM"},{"y":"PHAG.MI","t":"PHAG"},{"y":"PHPD.MI","t":"PHPD"},{"y":"PHPM.MI","t":"PHPM"},{"y":"PHPT.MI","t":"PHPT"},{"y":"PJSR.MI","t":"PJSR"},{"y":"QNTM.MI","t":"QNTM"},{"y":"QTOP.MI","t":"QTOP"},{"y":"QUAD.MI","t":"QUAD"},{"y":"RARE.MI","t":"RARE"},{"y":"RAYZ.MI","t":"RAYZ"},{"y":"RBOT.MI","t":"RBOT"},{"y":"REMX.MI","t":"REMX"},{"y":"RENW.MI","t":"RENW"},{"y":"REUS.MI","t":"REUS"},{"y":"REUSE.MI","t":"REUSE"},{"y":"RNRG.MI","t":"RNRG"},{"y":"ROBO.MI","t":"ROBO"},{"y":"ROE.MI","t":"ROE"},{"y":"SAUDI.MI","t":"SAUDI"},{"y":"SAUS.MI","t":"SAUS"},{"y":"SBIO.MI","t":"SBIO"},{"y":"SCITY.MI","t":"SCITY"},{"y":"SDG9.MI","t":"SDG9"},{"y":"SEMA.MI","t":"SEMA"},{"y":"SEME.MI","t":"SEME"},{"y":"SGBS.MI","t":"SGBS"},{"y":"SHEME.MI","t":"SHEME"},{"y":"SILV.MI","t":"SILV"},{"y":"SJPA.MI","t":"SJPA"},{"y":"SMCX.MI","t":"SMCX"},{"y":"SMEA.MI","t":"SMEA"},{"y":"SMH.MI","t":"SMH"},{"y":"SNSR.MI","t":"SNSR"},{"y":"SOLR.MI","t":"SOLR"},{"y":"SOYB.MI","t":"SOYB"},{"y":"SOYO.MI","t":"SOYO"},{"y":"SP1E.MI","t":"SP1E"},{"y":"SP5A.MI","t":"SP5A"},{"y":"SPXE.MI","t":"SPXE"},{"y":"SPXJ.MI","t":"SPXJ"},{"y":"SPY5.MI","t":"SPY5"},{"y":"SRIUC.MI","t":"SRIUC"},{"y":"SRSA.MI","t":"SRSA"},{"y":"STAW.MI","t":"STAW"},{"y":"DFSV.DE","t":"DFSV"},{"y":"STKX.MI","t":"STKX"},{"y":"STNX.MI","t":"STNX"},{"y":"STPX.MI","t":"STPX"},{"y":"STQX.MI","t":"STQX"},{"y":"STRX.MI","t":"STRX"},{"y":"STSX.MI","t":"STSX"},{"y":"STTX.MI","t":"STTX"},{"y":"STUX.MI","t":"STUX"},{"y":"SUGA.MI","t":"SUGA"},{"y":"SW2CHB.MI","t":"SW2CHB"},{"y":"SWDA.MI","t":"SWDA"},{"y":"SXLB.MI","t":"SXLB"},{"y":"SXLC.MI","t":"SXLC"},{"y":"SXLF.MI","t":"SXLF"},{"y":"SXLI.MI","t":"SXLI"},{"y":"SXLK.MI","t":"SXLK"},{"y":"SXLP.MI","t":"SXLP"},{"y":"SXLU.MI","t":"SXLU"},{"y":"SXLV.MI","t":"SXLV"},{"y":"SXLY.MI","t":"SXLY"},{"y":"T10A.MI","t":"T10A"},{"y":"TELE.MI","t":"TELE"},{"y":"TELEW.MI","t":"TELEW"},{"y":"TIP1A.MI","t":"TIP1A"},{"y":"TLCO.MI","t":"TLCO"},{"y":"TNO.MI","t":"TNO"},{"y":"TNOW.MI","t":"TNOW"},{"y":"TRVL.MI","t":"TRVL"},{"y":"TTFW.MI","t":"TTFW"},{"y":"TUR.MI","t":"TUR"},{"y":"U3O8.MI","t":"U3O8"},{"y":"UCRP.MI","t":"UCRP"},{"y":"UGAS.MI","t":"UGAS"},{"y":"UKE.MI","t":"UKE"},{"y":"UNIC.MI","t":"UNIC"},{"y":"URNJ.MI","t":"URNJ"},{"y":"URNU.MI","t":"URNU"},{"y":"US1.MI","t":"US1"},{"y":"US10C.MI","t":"US10C"},{"y":"US7.MI","t":"US7"},{"y":"USCBC.MI","t":"USCBC"},{"y":"USIC.MI","t":"USIC"},{"y":"USIG.MI","t":"USIG"},{"y":"USTEC.MI","t":"USTEC"},{"y":"UTI.MI","t":"UTI"},{"y":"UTIW.MI","t":"UTIW"},{"y":"VAGF.MI","t":"VAGF"},{"y":"VCDE.MI","t":"VCDE"},{"y":"VDCA.MI","t":"VDCA"},{"y":"VDCE.MI","t":"VDCE"},{"y":"VDEA.MI","t":"VDEA"},{"y":"VDST.MI","t":"VDST"},{"y":"VECA.MI","t":"VECA"},{"y":"VEGI.MI","t":"VEGI"},{"y":"VGEA.MI","t":"VGEA"},{"y":"VITA.MI","t":"VITA"},{"y":"VITU.MI","t":"VITU"},{"y":"VJPE.MI","t":"VJPE"},{"y":"VNGA20.MI","t":"VNGA20"},{"y":"VNGA40.MI","t":"VNGA40"},{"y":"VNGA60.MI","t":"VNGA60"},{"y":"VNGA80.MI","t":"VNGA80"},{"y":"VOLT.MI","t":"VOLT"},{"y":"VPN.MI","t":"VPN"},{"y":"VSCF.MI","t":"VSCF"},{"y":"VSGF.MI","t":"VSGF"},{"y":"VUCE.MI","t":"VUCE"},{"y":"VUKE.MI","t":"VUKE"},{"y":"VUSA.MI","t":"VUSA"},{"y":"WATC.MI","t":"WATC"},{"y":"WATT.MI","t":"WATT"},{"y":"WBLK.MI","t":"WBLK"},{"y":"WCBR.MI","t":"WCBR"},{"y":"WCCA.MI","t":"WCCA"},{"y":"WCLD.MI","t":"WCLD"},{"y":"WCOA.MI","t":"WCOA"},{"y":"WCOD.MI","t":"WCOD"},{"y":"WCOE.MI","t":"WCOE"},{"y":"WCOS.MI","t":"WCOS"},{"y":"WDEF.MI","t":"WDEF"},{"y":"WDNA.MI","t":"WDNA"},{"y":"WEAT.MI","t":"WEAT"},{"y":"WEB3.MI","t":"WEB3"},{"y":"WENT.MI","t":"WENT"},{"y":"WENU.MI","t":"WENU"},{"y":"WFIN.MI","t":"WFIN"},{"y":"WGRO.MI","t":"WGRO"},{"y":"WHEA.MI","t":"WHEA"},{"y":"WIND.MI","t":"WIND"},{"y":"WMAT.MI","t":"WMAT"},{"y":"WMGT.MI","t":"WMGT"},{"y":"WMIB.MI","t":"WMIB"},{"y":"WNAS.MI","t":"WNAS"},{"y":"WNDE.MI","t":"WNDE"},{"y":"WNDY.MI","t":"WNDY"},{"y":"WNRG.MI","t":"WNRG"},{"y":"WRNW.MI","t":"WRNW"},{"y":"WRTY.MI","t":"WRTY"},{"y":"WS5X.MI","t":"WS5X"},{"y":"WSLV.MI","t":"WSLV"},{"y":"WSPE.MI","t":"WSPE"},{"y":"WSPX.MI","t":"WSPX"},{"y":"WTAI.MI","t":"WTAI"},{"y":"WTEC.MI","t":"WTEC"},{"y":"WTEL.MI","t":"WTEL"},{"y":"WTI.MI","t":"WTI"},{"y":"WTID.MI","t":"WTID"},{"y":"WTRE.MI","t":"WTRE"},{"y":"WUTI.MI","t":"WUTI"},{"y":"X25E.MI","t":"X25E"},{"y":"X7PS.MI","t":"X7PS"},{"y":"XAGZ.MI","t":"XAGZ"},{"y":"XAIX.MI","t":"XAIX"},{"y":"XBAE.MI","t":"XBAE"},{"y":"XBAG.MI","t":"XBAG"},{"y":"XBLC.MI","t":"XBLC"},{"y":"XBNK.MI","t":"XBNK"},{"y":"XCHA.MI","t":"XCHA"},{"y":"XCS5.MI","t":"XCS5"},{"y":"XCTE.MI","t":"XCTE"},{"y":"XDAX.MI","t":"XDAX"},{"y":"XDBC.MI","t":"XDBC"},{"y":"XDEE.MI","t":"XDEE"},{"y":"XDER.MI","t":"XDER"},{"y":"XDEV.MI","t":"XDEV"},{"y":"XDG3.MI","t":"XDG3"},{"y":"XDG6.MI","t":"XDG6"},{"y":"XDG7.MI","t":"XDG7"},{"y":"XDGI.MI","t":"XDGI"},{"y":"XDRE.MI","t":"XDRE"},{"y":"XDW0.MI","t":"XDW0"},{"y":"XDWC.MI","t":"XDWC"},{"y":"XDWF.MI","t":"XDWF"},{"y":"XDWH.MI","t":"XDWH"},{"y":"XDWI.MI","t":"XDWI"},{"y":"XDWM.MI","t":"XDWM"},{"y":"XDWS.MI","t":"XDWS"},{"y":"XDWT.MI","t":"XDWT"},{"y":"XDWU.MI","t":"XDWU"},{"y":"XE01.MI","t":"XE01"},{"y":"XEON.MI","t":"XEON"},{"y":"XFNT.MI","t":"XFNT"},{"y":"XFVT.MI","t":"XFVT"},{"y":"XG11.MI","t":"XG11"},{"y":"XG12.MI","t":"XG12"},{"y":"XGEN.MI","t":"XGEN"},{"y":"XGLE.MI","t":"XGLE"},{"y":"XIFE.MI","t":"XIFE"},{"y":"XLBS.MI","t":"XLBS"},{"y":"XLCS.MI","t":"XLCS"},{"y":"XLES.MI","t":"XLES"},{"y":"XLFS.MI","t":"XLFS"},{"y":"XLIS.MI","t":"XLIS"},{"y":"XLKS.MI","t":"XLKS"},{"y":"XLPE.MI","t":"XLPE"},{"y":"XLPS.MI","t":"XLPS"},{"y":"XLUS.MI","t":"XLUS"},{"y":"XLVS.MI","t":"XLVS"},{"y":"XLYS.MI","t":"XLYS"},{"y":"D5BI.DE","t":"D5BI"},{"y":"XMME.MI","t":"XMME"},{"y":"XMOV.MI","t":"XMOV"},{"y":"XNGI.MI","t":"XNGI"},{"y":"XNNV.MI","t":"XNNV"},{"y":"XQUI.MI","t":"XQUI"},{"y":"XRES.MI","t":"XRES"},{"y":"XS8R.MI","t":"XS8R"},{"y":"XSFR.MI","t":"XSFR"},{"y":"XSGI.MI","t":"XSGI"},{"y":"XSMI.MI","t":"XSMI"},{"y":"XSX6.MI","t":"XSX6"},{"y":"XT01.MI","t":"XT01"},{"y":"XTC5.MI","t":"XTC5"},{"y":"XTIP.MI","t":"XTIP"},{"y":"XUSA.MI","t":"XUSA"},{"y":"XUTC.MI","t":"XUTC"},{"y":"XWTS.MI","t":"XWTS"},{"y":"XXSC.MI","t":"XXSC"},{"y":"XYP0.MI","t":"XYP0"},{"y":"ZINC.MI","t":"ZINC"},{"y":"EIDO","t":"EIDO"},{"y":"EIRL","t":"EIRL"},{"y":"IMOM","t":"IMOM"},{"y":"DBMFE.PA","t":"DBMFE"},{"y":"MEUD.PA","t":"MEUD"},{"y":"WRD.PA","t":"WRD"},{"y":"IB01.SW","t":"IB01"},{"y":"SDGPEX.SW","t":"SDGPEX"},{"y":"X13E.MI","t":"X13E"},{"y":"EM13.MI","t":"EM13"},{"y":"ERNE.MI","t":"ERNE"},{"y":"INFR.MI","t":"INFR"},{"y":"swda.MI","t":"SWDA_B"},{"y":"xdwd.MI","t":"XDWD"},{"y":"cw8.MI","t":"CW8"},{"y":"imeu.MI","t":"IMEU"},{"y":"inaa.MI","t":"INAA"},{"y":"SXLE.MI","t":"SXLE"},{"y":"MGIN.MI","t":"MGIN"},{"y":"STWX.MI","t":"STWX"},{"y":"STZX.MI","t":"STZX"},{"y":"SWRD.MI","t":"SWRD"},{"y":"600X.MI","t":"600X"},{"y":"EIS","t":"EIS"},{"y":"ENZL","t":"ENZL"},{"y":"EPHE","t":"EPHE"},{"y":"EPI","t":"EPI"},{"y":"EPOL","t":"EPOL"},{"y":"EPU","t":"EPU"},{"y":"EWA","t":"EWA"},{"y":"EWC","t":"EWC"},{"y":"EWD","t":"EWD"},{"y":"EWG","t":"EWG"},{"y":"EWH","t":"EWH"},{"y":"EWI","t":"EWI"},{"y":"EWJ","t":"EWJ"},{"y":"EWK","t":"EWK"},{"y":"EWL","t":"EWL"},{"y":"EWM","t":"EWM"},{"y":"EWN","t":"EWN"},{"y":"EWO","t":"EWO"},{"y":"EWP","t":"EWP"},{"y":"EWQ","t":"EWQ"},{"y":"EWS","t":"EWS"},{"y":"EWT","t":"EWT"},{"y":"EWU","t":"EWU"},{"y":"EWW","t":"EWW"},{"y":"EWY","t":"EWY"},{"y":"EWZ","t":"EWZ"},{"y":"EZA","t":"EZA"},{"y":"FM.TO","t":"FM"},{"y":"GREK","t":"GREK"},{"y":"GXG","t":"GXG"},{"y":"ICLN","t":"ICLN"},{"y":"ILF","t":"ILF"},{"y":"MES","t":"MES"},{"y":"NORW","t":"NORW"},{"y":"QQQ","t":"QQQ"},{"y":"SPLV","t":"SPLV"},{"y":"SPY","t":"SPY"},{"y":"THD","t":"THD"},{"y":"UAE","t":"UAE"},{"y":"VNM","t":"VNM"},{"y":"VPL","t":"VPL"},{"y":"ADS.DE","t":"ADS"},{"y":"ADYEN.AS","t":"ADYEN"},{"y":"AI.PA","t":"AI"},{"y":"AIR.PA","t":"AIR"},{"y":"AM.PA","t":"AM"},{"y":"ARGX","t":"ARGX"},{"y":"ASM.SW","t":"ASM"},{"y":"ASML.SW","t":"ASML"},{"y":"BEI.DE","t":"BEI"},{"y":"CBK.DE","t":"CBK"},{"y":"DB1.DE","t":"DB1"},{"y":"DIM.PA","t":"DIM"},{"y":"DSY.PA","t":"DSY"},{"y":"DTE.DE","t":"DTE"},{"y":"EL.PA","t":"EL"},{"y":"ELE.MC","t":"ELE"},{"y":"ENR.DE","t":"ENR"},{"y":"FER.MC","t":"FER"},{"y":"HEI.DE","t":"HEI"},{"y":"HO.PA","t":"HO"},{"y":"IFX.DE","t":"IFX"},{"y":"ITX.VI","t":"ITX"},{"y":"KNEBV.HE","t":"KNEBV"},{"y":"LDO.MI","t":"LDO"},{"y":"LR.PA","t":"LR"},{"y":"MC.PA","t":"MC"},{"y":"NOKIA.HE","t":"NOKIA"},{"y":"OR.PA","t":"OR"},{"y":"PRX.AS","t":"PRX"},{"y":"PRY.MI","t":"PRY"},{"y":"RACE.MI","t":"RACE"},{"y":"RHM.DE","t":"RHM"},{"y":"RMS.PA","t":"RMS"},{"y":"RYA.IR","t":"RYA"},{"y":"SAF.PA","t":"SAF"},{"y":"SAP.DE","t":"SAP"},{"y":"SHL.DE","t":"SHL"},{"y":"SIE.DE","t":"SIE"},{"y":"SRT.DE","t":"SRT"},{"y":"STMMI.PA","t":"STMMI"},{"y":"SU.PA","t":"SU"},{"y":"UCB","t":"UCB"},{"y":"UCG.MI","t":"UCG"},{"y":"UMG.AS","t":"UMG"},{"y":"WKL.VI","t":"WKL"}]

# Dedup su symbol yahoo (fix EIMI.MI doppio + altri eventuali doppioni)
_seen = set()
TICKERS = []
for _t in TICKERS_RAW:
    if _t['y'] not in _seen:
        _seen.add(_t['y']); TICKERS.append(_t)

# ═══════════════════════════════════════════════════════
#  INDICATORI — stessa identica logica di raptor_fetch.py,
#  qui riscritti come array su tutta la serie (non solo ultimo valore)
#  per non dover più ricalcolare nulla nel browser.
# ═══════════════════════════════════════════════════════

def calc_kama(close, n=10, fast=2, slow=30):
    fast_sc = 2/(fast+1); slow_sc = 2/(slow+1)
    kama = [None]*len(close)
    if len(close) <= n: return kama
    kama[n] = close[n]
    for i in range(n+1, len(close)):
        direction  = abs(close[i] - close[i-n])
        volatility = sum(abs(close[j] - close[j-1]) for j in range(i-n+1, i+1))
        er = direction/volatility if volatility != 0 else 0
        sc = (er*(fast_sc - slow_sc) + slow_sc)**2
        kama[i] = kama[i-1] + sc*(close[i] - kama[i-1])
    return kama

def calc_sar_array(high, low, af0=0.02, af_max=0.20):
    n = len(high)
    sar_arr = [None]*n; bull_arr = [None]*n
    if n < 5: return sar_arr, bull_arr
    sar = low[0]; ep = high[0]; af = af0; bull = True
    sar_arr[0] = round(sar,4); bull_arr[0] = bull
    for i in range(1, n):
        if bull:
            new_sar = sar + af*(ep-sar)
            new_sar = min(new_sar, low[max(0,i-1)], low[max(0,i-2)])
            if low[i] < new_sar:
                bull = False; new_sar = ep; ep = low[i]; af = af0
            else:
                if high[i] > ep: ep = high[i]; af = min(af+af0, af_max)
        else:
            new_sar = sar + af*(ep-sar)
            new_sar = max(new_sar, high[max(0,i-1)], high[max(0,i-2)])
            if high[i] > new_sar:
                bull = True; new_sar = ep; ep = high[i]; af = af0
            else:
                if low[i] < ep: ep = low[i]; af = min(af+af0, af_max)
        sar = new_sar; sar_arr[i] = round(sar,4); bull_arr[i] = bull
    return sar_arr, bull_arr

def calc_ao_array(high, low):
    mid = [(h+l)/2 for h,l in zip(high,low)]
    result = [None]*len(mid)
    for i in range(33, len(mid)):
        sma5  = sum(mid[i-4:i+1])/5
        sma34 = sum(mid[i-33:i+1])/34
        result[i] = round(sma5 - sma34, 4)
    return result

def calc_rsi_array(close, n=14):
    result = [None]*len(close)
    if len(close) < n+2: return result
    for i in range(n, len(close)):
        gains=0.0; losses=0.0
        for j in range(i-n+1, i+1):
            d = close[j]-close[j-1]
            if d>0: gains+=d
            else: losses+=-d
        ag=gains/n; al=losses/n
        result[i] = round(100-100/(1+ag/al),2) if al>0 else 100.0
    return result

def calc_er_array(close, n=10):
    result = [0]*len(close)
    for i in range(n, len(close)):
        direction  = abs(close[i]-close[i-n])
        volatility = sum(abs(close[j]-close[j-1]) for j in range(i-n+1,i+1))
        result[i] = round(direction/volatility,4) if volatility != 0 else 0
    return result

def calc_baffetti_array(high, low):
    """Barre consecutive con mid-price in salita — identica logica di calc_baffetti() in raptor_fetch.py"""
    mid = [(h+l)/2 for h,l in zip(high,low)]
    result = [0]*len(mid)
    streak = 0
    for i in range(1, len(mid)):
        streak = streak+1 if mid[i] > mid[i-1] else 0
        result[i] = streak
    return result

def calc_mm_align_array(close):
    n = len(close)
    result = [False]*n
    cum = [0.0]*(n+1)
    for i in range(n): cum[i+1] = cum[i] + close[i]
    def avg(i, w):
        return (cum[i+1]-cum[i+1-w])/w if i+1 >= w else None
    for i in range(n):
        mm20, mm50, mm100 = avg(i,20), avg(i,50), avg(i,100)
        if mm20 is not None and mm50 is not None and mm100 is not None:
            result[i] = close[i] > mm20 > mm50 > mm100
    return result

def calc_cross_days_array(close, kama):
    n = len(close)
    result = [999]*n
    last_flip = None; prev_above = None
    for i in range(n):
        if kama[i] is None:
            continue
        above = close[i] > kama[i]
        if prev_above is None:
            prev_above = above; last_flip = i; result[i] = 0; continue
        if above != prev_above:
            last_flip = i; prev_above = above
        result[i] = i - last_flip
    return result

def calc_ao_improving_array(ao):
    n = len(ao)
    result = [False]*n
    for i in range(1, n):
        if ao[i] is not None and ao[i-1] is not None and ao[i] > ao[i-1]:
            result[i] = True
    return result

def calc_segnale_array(close, kama, er_arr, baff_arr, ao_imp_arr, sar_bull_arr, cross_arr, mm_arr, rsi_arr):
    """Stessa cascata di priorità di calc_segnale() in raptor_fetch.py, applicata barra per barra."""
    n = len(close)
    result = [None]*n
    for i in range(n):
        if kama[i] is None or sar_bull_arr[i] is None:
            continue
        lk = kama[i]; lc = close[i]
        above_kama = lc > lk if lk else False
        sar_bull = sar_bull_arr[i]; cross = cross_arr[i]
        ao_imp = ao_imp_arr[i]; baff = baff_arr[i]
        er = er_arr[i]; mm_align = mm_arr[i]
        rsi = rsi_arr[i] if rsi_arr[i] is not None else 50
        if sar_bull and cross <= 3 and ao_imp:
            result[i] = 'BUY1'
        elif above_kama and baff >= 2:
            result[i] = 'BUY2'
        elif above_kama and er >= 0.50 and baff >= 3 and mm_align:
            result[i] = 'BUY3'
        elif not above_kama and not sar_bull:
            result[i] = 'EXIT2'
        elif not sar_bull:
            result[i] = 'EXIT1'
        else:
            near_kama = abs(lc-lk)/lk < 0.03 if lk and lk > 0 else False
            if er < 0.30 and rsi < 30 and ao_imp and (near_kama or not above_kama):
                result[i] = 'MEAN REV'
            else:
                result[i] = 'WATCH'
    return result

# ═══════════════════════════════════════════════════════
#  RENKO — brick adattivo su ATR(14)
# ═══════════════════════════════════════════════════════

def calc_atr(high, low, close, n=14):
    trs = []
    for i in range(len(close)):
        if i == 0: trs.append(high[i]-low[i])
        else: trs.append(max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1])))
    if len(trs) < n+1: return None
    atr = sum(trs[1:n+1])/n
    for i in range(n+1, len(trs)):
        atr = (atr*(n-1) + trs[i])/n
    return atr

def calc_renko(dates, close, brick_size):
    """Renko standard: continuazione di trend = 1 brick_size dal livello
    corrente; inversione di trend = 2 brick_size (convenzione classica,
    altrimenti il rumore genererebbe inversioni continue). Brick adattivo
    = ATR(14) del ticker, quindi coerente con la sua volatilità reale.
    NOTA: la versione precedente bloccava la direzione al primo mattoncino
    (bug — poteva salire ma non scendere mai più, o viceversa)."""
    if not brick_size or brick_size <= 0 or len(close) < 2:
        return []
    bricks = []
    level = close[0]
    direction = 0  # 0=nessun trend ancora, 1=rialzista, -1=ribassista
    for i in range(1, len(close)):
        price = close[i]
        d = dates[i] if i < len(dates) else None
        while True:
            if direction >= 0 and price >= level + brick_size:
                new_level = level + brick_size
                bricks.append({'o': round(level,4), 'c': round(new_level,4), 'dir': 1, 'd': d})
                level = new_level; direction = 1; continue
            if direction <= 0 and price <= level - brick_size:
                new_level = level - brick_size
                bricks.append({'o': round(level,4), 'c': round(new_level,4), 'dir': -1, 'd': d})
                level = new_level; direction = -1; continue
            if direction == 1 and price <= level - 2*brick_size:
                new_level = level - brick_size
                bricks.append({'o': round(level,4), 'c': round(new_level,4), 'dir': -1, 'd': d})
                level = new_level; direction = -1; continue
            if direction == -1 and price >= level + 2*brick_size:
                new_level = level + brick_size
                bricks.append({'o': round(level,4), 'c': round(new_level,4), 'dir': 1, 'd': d})
                level = new_level; direction = 1; continue
            break
    return bricks[-200:]

def calc_sar_streak_array(sarBull_arr):
    """Giorni consecutivi nella direzione SAR corrente (0 = appena flippato)."""
    n = len(sarBull_arr)
    streak = [0]*n
    for i in range(1, n):
        if sarBull_arr[i] is None or sarBull_arr[i-1] is None:
            continue
        streak[i] = streak[i-1]+1 if sarBull_arr[i]==sarBull_arr[i-1] else 0
    return streak

def sanitize_nan(obj):
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict): return {k: sanitize_nan(v) for k,v in obj.items()}
    if isinstance(obj, list): return [sanitize_nan(v) for v in obj]
    return obj

def fmt(arr):
    return [round(v,4) if isinstance(v,(int,float)) else v for v in arr]

# ═══════════════════════════════════════════════════════
#  PROCESS TICKER
# ═══════════════════════════════════════════════════════
def process_ticker(info):
    symbol = info['y']
    try:
        tk = yf.Ticker(symbol)
        hist_d = tk.history(period='2y', interval='1d', timeout=20)
        if hist_d.empty or len(hist_d) < 60:
            return None

        opens  = [round(float(x),4) for x in hist_d['Open'].values]
        highs  = [round(float(x),4) for x in hist_d['High'].values]
        lows   = [round(float(x),4) for x in hist_d['Low'].values]
        closes = [round(float(x),4) for x in hist_d['Close'].values]
        vols   = [int(x) for x in hist_d['Volume'].values]
        dates  = [ts.strftime('%Y-%m-%d') for ts in hist_d.index]
        ts_d   = [int(ts.timestamp()) for ts in hist_d.index]
        d_bars = [[ts_d[i], opens[i], highs[i], lows[i], closes[i], vols[i]] for i in range(len(closes))]

        time.sleep(0.3)
        h_bars = []
        try:
            hist_h = tk.history(period='5d', interval='1h', timeout=20)
            if not hist_h.empty:
                ho=[round(float(x),4) for x in hist_h['Open'].values]
                hh=[round(float(x),4) for x in hist_h['High'].values]
                hl=[round(float(x),4) for x in hist_h['Low'].values]
                hc=[round(float(x),4) for x in hist_h['Close'].values]
                hv=[int(x) for x in hist_h['Volume'].values]
                ht=[int(ts.timestamp()) for ts in hist_h.index]
                h_bars=[[ht[i],ho[i],hh[i],hl[i],hc[i],hv[i]] for i in range(len(hc))]
        except Exception:
            pass

        # ── Indicatori su daily ──
        kama_arr = calc_kama(closes)
        sar_arr, sarBull_arr = calc_sar_array(highs, lows)
        ao_arr = calc_ao_array(highs, lows)
        rsi_arr = calc_rsi_array(closes)
        rsi5_arr = calc_rsi_array(closes, n=5)
        er_arr = calc_er_array(closes)
        baff_arr = calc_baffetti_array(highs, lows)
        mm_arr = calc_mm_align_array(closes)
        cross_arr = calc_cross_days_array(closes, kama_arr)
        ao_imp_arr = calc_ao_improving_array(ao_arr)
        segnale_arr = calc_segnale_array(closes, kama_arr, er_arr, baff_arr, ao_imp_arr,
                                          sarBull_arr, cross_arr, mm_arr, rsi_arr)
        sarStreak_arr = calc_sar_streak_array(sarBull_arr)

        # ── Indicatori su hourly (stesso set, serve al pannello prezzo per tf 5h/1d) ──
        kama_h, sar_h, sarBull_h = [], [], []
        if len(h_bars) > 12:
            hc = [b[4] for b in h_bars]; hh = [b[2] for b in h_bars]; hl = [b[3] for b in h_bars]
            kama_h = calc_kama(hc)
            sar_h, sarBull_h = calc_sar_array(hh, hl)

        # ── ATR + Renko (brick adattivo) ──
        atr = calc_atr(highs, lows, closes, 14)
        brick = round(atr, 4) if atr else None
        renko = calc_renko(dates, closes, brick) if brick else []

        # ── Suggerimento uscita ML: solo se il segnale ATTUALE (ultima barra) è BUY1/BUY2 ──
        ml_exit = None
        last_seg = segnale_arr[-1] if segnale_arr else None
        if _ML_EXIT is not None and last_seg in ('BUY1', 'BUY2'):
            try:
                i = len(closes) - 1
                vol_avg20 = sum(vols[max(0,i-20):i])/max(1,min(20,i)) if i > 0 else 1
                feat = {
                    'er': er_arr[i], 'baff': baff_arr[i],
                    'rsi': rsi_arr[i] if rsi_arr[i] is not None else 50,
                    'ao': ao_arr[i] if ao_arr[i] is not None else 0,
                    'cross_days': cross_arr[i], 'mm_align': int(mm_arr[i]),
                    'atr_pct': (atr/closes[i]*100) if atr and closes[i] else 0,
                    'vol_ratio': (vols[i]/vol_avg20) if vol_avg20 else 1,
                    'tier_buy1': 1 if last_seg == 'BUY1' else 0,
                }
                X = [[feat[f] for f in _ML_EXIT['features']]]
                peak_pct = float(_ML_EXIT['reg_peak'].predict(X)[0])
                days_peak = float(_ML_EXIT['reg_days'].predict(X)[0])
                ml_exit = {'peak_return_pct': round(peak_pct, 2), 'days_to_peak': round(days_peak, 1)}
            except Exception as e:
                print(f"  ATTENZIONE ML uscita {symbol}: {e}")

        result = {
            'ticker': info['t'], 'yahoo': symbol,
            'd': d_bars, 'h': h_bars,
            'kama_d': fmt(kama_arr), 'sar_d': fmt(sar_arr), 'sarBull_d': sarBull_arr,
            'ao_d': fmt(ao_arr), 'rsi_d': fmt(rsi_arr), 'rsi5_d': fmt(rsi5_arr), 'baff_d': baff_arr,
            'segnale_d': segnale_arr,
            'er_d': fmt(er_arr), 'crossDays_d': cross_arr, 'mmAlign_d': mm_arr,
            'sarStreak_d': sarStreak_arr,
            'kama_h': fmt(kama_h), 'sar_h': fmt(sar_h), 'sarBull_h': sarBull_h,
            'atr': round(atr,4) if atr else None,
            'renko_brick': brick, 'renko': renko,
            'ml_exit': ml_exit,
        }
        return sanitize_nan(result)
    except Exception as e:
        print(f"  ERR {symbol}: {e}")
        return None

# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════
def main():
    now = datetime.datetime.now()
    print(f"RAPTOR Chart Fetch v3.0 — {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"Ticker unici: {len(TICKERS)}")

    os.makedirs('data/charts', exist_ok=True)

    ok = 0; errors = 0
    index = []
    for i, info in enumerate(TICKERS):
        result = process_ticker(info)
        if result:
            fname = info['y'].replace('.', '_') + '.json'
            with open(f"data/charts/{fname}", 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
            index.append({'t': info['t'], 'y': info['y'], 'f': fname})
            ok += 1
        else:
            errors += 1
        if (i+1) % 50 == 0:
            print(f"  {i+1}/{len(TICKERS)} — ok:{ok} errori:{errors}")
        time.sleep(0.3)

    meta = {
        'timestamp': now.isoformat(),
        'timestamp_it': now.strftime('%d/%m/%Y %H:%M'),
        'ok': ok, 'errors': errors,
        'index': index,
    }
    with open('data/charts/index.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))

    print(f"\n✅ Salvati {ok} file in data/charts/ — {errors} errori")

if __name__ == '__main__':
    main()
