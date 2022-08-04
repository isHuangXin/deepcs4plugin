import axios from 'axios';

const PROTOCAL_PREFIX = "http://";


class CodeFetcher {
    private fetcherUrl : string;

    constructor(url : string, port : number) {
        this.fetcherUrl = PROTOCAL_PREFIX + url + `:${port}`;
    }

    async fetchCode(query : string, nresult : number) : Promise<Array<[string, number]>> {
        return axios({
            method: 'get',
            url: this.fetcherUrl,
            headers: {"query" : query, "nresult" : nresult},
            responseType: 'json',
            responseEncoding: 'utf-8'
        }
        ).then(
            (res) => {
                return res.data;
            }
        );
    }
}

export default CodeFetcher;