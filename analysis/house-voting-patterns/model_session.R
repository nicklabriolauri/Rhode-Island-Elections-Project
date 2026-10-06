suppressPackageStartupMessages({library(jsonlite);library(pscl);library(wnominate)})
set.seed(20261006)
x<-read.csv("model_matrix.csv",check.names=FALSE,na.strings="")
m<-as.matrix(x[,-1]);storage.mode(m)<-"numeric";rownames(m)<-x$legislator
roster<-fromJSON("representatives.json");meta<-roster[match(rownames(m),roster$name),c("district","party","current")];rownames(meta)<-rownames(m)
rolls<-read.csv("rollcalls.csv",check.names=FALSE)
m[m==0]<-6;m[is.na(m)]<-9
make_rc<-function(mat) rollcall(mat,yea=1,nay=6,missing=9,notInLegis=0,legis.names=rownames(mat),vote.names=colnames(mat),legis.data=meta)
rc<-make_rc(m)
dir.create("results",showWarnings=FALSE)
# First try the package's native bootstrap; preserve any failure and use point estimates if necessary.
if("--reuse-fit" %in% commandArgs(trailingOnly=TRUE)) {
 fit<-readRDS("results/session_fit.rds")
 bootstrap_ok<-fromJSON("results/model_status.json")$native_bootstrap_success
} else {
attempt<-tryCatch(wnominate(rc,dims=1,minvotes=20,lop=.025,trials=50,polarity="Michael Chippendale",verbose=FALSE),error=function(e)e)
bootstrap_ok<-!inherits(attempt,"error")
if(bootstrap_ok){fit<-attempt}else{
 writeLines(conditionMessage(attempt),"results/native_bootstrap_error.txt")
 set.seed(20261006)
 fit<-wnominate(rc,dims=1,minvotes=20,lop=.025,trials=3,polarity="Michael Chippendale",verbose=FALSE)
 fit$legislators[,"se1D"]<-NA_real_
}
}
rownames(fit$rollcalls)<-colnames(m)
saveRDS(fit,"results/session_fit.rds")
write.csv(fit$legislators,"results/legislator_estimates.csv",row.names=TRUE)
write.csv(fit$rollcalls,"results/rollcall_estimates.csv",row.names=TRUE)
capture.output(summary(fit),file="results/model_summary.txt")
capture.output(sessionInfo(),file="results/R_session.txt")
retained<-rownames(fit$legislators)[!is.na(fit$legislators[,"coord1D"])]
retained_votes<-rownames(fit$rollcalls)[!is.na(fit$rollcalls[,"midpoint1D"])]
write_json(list(native_bootstrap_success=bootstrap_ok,retained_legislators=retained,excluded_legislators=setdiff(rownames(m),retained),retained_votes=length(retained_votes)),"results/model_status.json",pretty=TRUE,auto_unbox=TRUE)
# Robustness fits: compare within chamber, same axis anchor. Annual coordinates are separately scaled.
checks<-list()
configs<-list(cutoff_5pct=list(columns=colnames(m),lop=.05),cutoff_10pct=list(columns=colnames(m),lop=.1),
 year_2025=list(columns=colnames(m)[grepl("HOU-2025",colnames(m))],lop=.025),
 year_2026=list(columns=colnames(m)[grepl("HOU-2026",colnames(m))],lop=.025),
 passage_only=list(columns=rolls$rollcall_id[(tolower(rolls$valid)=="true") & rolls$motion_class=="Passage"],lop=.025))
for(n in names(configs)){
 cfg<-configs[[n]]
 alt<-tryCatch(wnominate(make_rc(m[,cfg$columns,drop=FALSE]),dims=1,minvotes=20,lop=cfg$lop,trials=3,polarity="Michael Chippendale",verbose=FALSE),error=function(e)e)
 if(inherits(alt,"error")){checks[[n]]<-list(error=conditionMessage(alt));next}
 alt$legislators[,"se1D"]<-NA_real_
 saveRDS(alt,paste0("results/",n,"_fit.rds"))
 write.csv(alt$legislators,paste0("results/",n,"_estimates.csv"),row.names=TRUE)
 a<-fit$legislators[,"coord1D"];b<-alt$legislators[,"coord1D"]
 names(a)<-rownames(fit$legislators);names(b)<-rownames(alt$legislators)
 common<-intersect(names(a)[!is.na(a)],names(b)[!is.na(b)])
 checks[[n]]<-list(common_legislators=length(common),votes_used=sum(!is.na(alt$rollcalls[,"midpoint1D"])),spearman=cor(a[common],b[common],method="spearman"))
}
write_json(checks,"results/sensitivity.json",pretty=TRUE,auto_unbox=TRUE)
# Cross-year ordering check: not a longitudinal common-space score.
annual_a<-readRDS("results/year_2025_fit.rds");annual_b<-readRDS("results/year_2026_fit.rds")
a<-annual_a$legislators[,"coord1D"];names(a)<-rownames(annual_a$legislators)
b<-annual_b$legislators[,"coord1D"];names(b)<-rownames(annual_b$legislators)
common<-intersect(names(a)[!is.na(a)],names(b)[!is.na(b)])
write_json(list(common_legislators=length(common),spearman=cor(a[common],b[common],method="spearman"),note="Separate annual fits; coordinates are not directly comparable as ideological movement."),"results/annual_comparison.json",pretty=TRUE,auto_unbox=TRUE)
# Identify identical observed patterns among retained informative votes.
patterns<-apply(m[retained,retained_votes,drop=FALSE],1,paste,collapse=",")
groups<-split(names(patterns),patterns);groups<-groups[lengths(groups)>1]
writeLines(vapply(groups,paste,character(1),collapse="; "),"results/identical_voting_patterns.txt")
